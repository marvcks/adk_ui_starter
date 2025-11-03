"""
Message processing service
Handles message validation, processing, and response generation
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import uuid
import json

from google.adk import Runner
from google.genai import types

from core.event_handlers import EventProcessor, EventContext, EventType
from core.state_machine import SessionState, StateMachine
from config.photon_config import CHARGING_ENABLED
from services.photon_service import get_photon_service

# Import message types from core module
from core.message_types import (
    MessageType, MessageStatus, Message, UserMessage,
    AssistantMessage, ToolMessage, SystemMessage
)

logger = logging.getLogger(__name__)


class MessageService:
    """Service for processing messages and managing conversations"""
    
    def __init__(self, event_processor: EventProcessor, websocket=None):
        self.event_processor = event_processor
        self.message_history: Dict[str, List[Message]] = {}
        self.processing_messages: Dict[str, Dict[str, Any]] = {}
        self.websocket = websocket  # 添加WebSocket引用
    
    def set_websocket(self, websocket):
        """设置WebSocket引用"""
        self.websocket = websocket
    
    async def process_user_message(self, 
                                 session_id: str, 
                                 user_id: str, 
                                 content: str,
                                 runner: Runner) -> Dict[str, Any]:
        """Process a user message and generate response"""
        
        # Create message context
        message_id = str(uuid.uuid4())
        context = EventContext(
            session_id=session_id,
            user_id=user_id,
            message_id=message_id,
            timestamp=datetime.now(),
            metadata={'content': content}
        )
        
        try:
            # Record message received event
            await self.event_processor.process_event(
                EventType.TOOL_CALL_STARTED,  # Using this as a placeholder for message received
                context,
                {'content': content, 'type': 'user_message'}
            )
            
            # Create user message
            user_message = UserMessage(
                content=content,
                session_id=session_id
            )
            
            # Store message in history
            if session_id not in self.message_history:
                self.message_history[session_id] = []
            self.message_history[session_id].append(user_message)
            
            logger.info(f"用户消息已保存到会话 {session_id}: {content[:50]}...")
            logger.info(f"会话 {session_id} 当前消息数量: {len(self.message_history[session_id])}")
            
            # Process with agent
            response = await self._process_with_agent(runner, content, context)
            
            # Create assistant message
            assistant_message = AssistantMessage(
                content=response.get('content', ''),
                session_id=session_id,
                tool_calls=response.get('tool_calls', [])
            )
            
            # Store assistant response
            self.message_history[session_id].append(assistant_message)
            
            logger.info(f"助手消息已保存到会话 {session_id}: {response.get('content', '')[:50]}...")
            logger.info(f"会话 {session_id} 当前消息数量: {len(self.message_history[session_id])}")
            
            # 执行光子收费（如果启用）- 参考原始代码的收费逻辑
            charge_result = None
            if CHARGING_ENABLED:
                charge_result = await self._process_photon_charging(
                    response.get('usage_metadata', {}),
                    response.get('tool_calls', []),
                    context
                )
            
            # Record completion event
            await self.event_processor.process_event(
                EventType.RESPONSE_GENERATED,
                context,
                {'content': response.get('content', ''), 'tool_calls': response.get('tool_calls', [])}
            )
            
            return {
                'success': True,
                'message_id': message_id,
                'response': response,
                'user_message': user_message.to_dict(),
                'assistant_message': assistant_message.to_dict(),
                'charge_result': charge_result  # 添加收费结果
            }
            
        except Exception as e:
            logger.error(f"Error processing user message: {e}")
            
            # Record error event
            await self.event_processor.process_event(
                EventType.ERROR_OCCURRED,
                context,
                {'error': str(e)}
            )
            
            return {
                'success': False,
                'message_id': message_id,
                'error': str(e)
            }
    
    async def _process_with_agent(self, 
                                 runner: Runner, 
                                 content: str, 
                                 context: EventContext) -> Dict[str, Any]:
        """Process message with the agent using Google ADK - 参考 ADK Web 实现"""
        
        # Create content for agent
        agent_content = types.Content(
            role='user',
            parts=[types.Part(text=content)]
        )
        
        # Track events and tool calls - 参考 ADK Web 的事件追踪方式
        all_events = []
        tool_calls = []
        seen_tool_calls = set()
        seen_tool_responses = set()
        long_running_tool_ids = set()  # 跟踪长期运行的工具ID
        
        # Process with agent
        async for event in runner.run_async(
            new_message=agent_content,
            user_id=context.user_id,
            session_id=context.session_id
        ):
            all_events.append(event)
            # logger.info(f"Received event: {type(event).__name__}")
            # logger.debug(f"Received event: {type(event).__name__}")
            
            # 参考 ADK Web: 检查长期运行的工具ID
            if hasattr(event, 'long_running_tool_ids') and event.long_running_tool_ids:
                long_running_tool_ids.update(event.long_running_tool_ids)
                logger.info(f"Long running tool IDs detected: {event.long_running_tool_ids}")
            
            # Process tool calls - 参考 ADK Web 的工具调用处理
            if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                for part in event.content.parts:
                    # Handle function calls (tool calls) - 参考 ADK Web 的 function_call 处理
                    if hasattr(part, 'function_call') and part.function_call:
                        await self._handle_tool_call(
                            part.function_call, 
                            event, 
                            context, 
                            seen_tool_calls,
                            long_running_tool_ids
                        )
                        tool_calls.append({
                            'name': getattr(part.function_call, 'name', 'unknown'),
                            'id': getattr(part.function_call, 'id', 'unknown'),
                            'status': 'executing'
                        })
                    
                    # Handle function responses (tool results) - 参考 ADK Web 的 function_response 处理
                    elif hasattr(part, 'function_response') and part.function_response:
                        await self._handle_tool_response(part.function_response, context, seen_tool_responses)
        
        # Extract final response
        final_response = self._extract_final_response(all_events)
        
        # Extract token usage information - 参考原始代码的token提取逻辑
        usage_metadata = self._extract_usage_metadata(all_events)
        
        return {
            'content': final_response,
            'tool_calls': tool_calls,
            'usage_metadata': usage_metadata,  # 添加token使用信息
            'events': all_events,  # 保留事件信息用于后续处理
            'events_count': len(all_events),
            'long_running_tool_ids': list(long_running_tool_ids)  # 返回长期运行的工具ID列表
        }
    
    async def _handle_tool_call(self, function_call, event, context: EventContext, seen_tool_calls: set, long_running_tool_ids: set):
        """Handle tool call event and send to frontend - 参考 ADK Web 实现"""
        tool_name = getattr(function_call, 'name', 'unknown')
        tool_id = getattr(function_call, 'id', tool_name)
        
        # Avoid duplicate tool calls
        if tool_id in seen_tool_calls:
            return
        seen_tool_calls.add(tool_id)
        
        # 参考 ADK Web: 检查是否为长期运行的工具
        is_long_running = False
        if hasattr(function_call, 'id') and function_call.id in long_running_tool_ids:
            is_long_running = True
            logger.debug(f"Long running tool detected: {tool_name} (ID: {tool_id})")
        
        # Record tool call started event
        await self.event_processor.process_event(
            EventType.TOOL_CALL_STARTED,
            context,
            {
                'tool_id': tool_id,
                'name': tool_name,
                'is_long_running': is_long_running
            }
        )
        
        # Create tool message for history - 参考 ADK Web 的消息格式
        from core.message_types import ToolMessage
        tool_message = ToolMessage(
            content=f"正在执行工具: {tool_name}",
            tool_name=tool_name,
            tool_id=tool_id,
            tool_status=MessageStatus.PROCESSING,
            is_long_running=is_long_running,
            session_id=context.session_id
        )
        
        # Save tool message to history
        if context.session_id not in self.message_history:
            self.message_history[context.session_id] = []
        self.message_history[context.session_id].append(tool_message)
        
        logger.info(f"工具调用消息已保存到会话 {context.session_id}: {tool_name} (long_running: {is_long_running})")
        
        # Send tool call status to frontend - 参考 ADK Web 的消息格式
        if self.websocket:
            try:
                # 提取工具调用的输入参数 - 参考 ADK Web 的 args 字段
                tool_args = getattr(function_call, 'args', None)
                
                await self.websocket.send_json({
                    "type": "tool",
                    "tool_name": tool_name,
                    "tool_id": tool_id,
                    "status": "executing",
                    "is_long_running": is_long_running,
                    "args": tool_args,  # 添加输入参数
                    "timestamp": datetime.now().isoformat(),
                    "session_id": context.session_id
                })
                logger.info(f"Tool call status sent to frontend: {tool_name} with args: {tool_args}")
            except Exception as e:
                logger.error(f"Failed to send tool call status to frontend: {e}")
        
        logger.info(f"Tool call detected: {tool_name} (ID: {tool_id}, long_running: {is_long_running})")
    
    async def _handle_tool_response(self, function_response, context: EventContext, seen_tool_responses: set):
        """Handle tool response event and send to frontend - 参考 ADK Web 实现"""
        tool_name = getattr(function_response, 'name', 'unknown')
        response_id = f"{tool_name}_response"
        
        if hasattr(function_response, 'id'):
            response_id = function_response.id
        
        # Avoid duplicate responses
        if response_id in seen_tool_responses:
            return
        seen_tool_responses.add(response_id)
        
        # Get response data - 参考 ADK Web 的响应处理
        response_data = getattr(function_response, 'response', None)
        result_str = self._format_tool_response(response_data)
        
        # Record tool call completed event
        await self.event_processor.process_event(
            EventType.TOOL_CALL_COMPLETED,
            context,
            {
                'tool_id': response_id,
                'name': tool_name,
                'result': result_str
            }
        )
        
        # Create tool completion message for history - 参考 ADK Web 的消息格式
        from core.message_types import ToolMessage
        tool_completion_message = ToolMessage(
            content=f"工具执行完成: {tool_name}",
            tool_name=tool_name,
            tool_id=response_id,
            tool_status=MessageStatus.COMPLETED,
            result=result_str,
            session_id=context.session_id
        )
        
        # Save tool completion message to history
        if context.session_id not in self.message_history:
            self.message_history[context.session_id] = []
        self.message_history[context.session_id].append(tool_completion_message)
        
        logger.info(f"工具完成消息已保存到会话 {context.session_id}: {tool_name} (ID: {response_id})")
        
        # Send tool completion status to frontend - 参考 ADK Web 的消息格式
        if self.websocket:
            try:
                await self.websocket.send_json({
                    "type": "tool",
                    "tool_name": tool_name,
                    "tool_id": response_id,
                    "status": "completed",
                    "result": result_str,
                    "timestamp": datetime.now().isoformat(),
                    "session_id": context.session_id
                })
                logger.info(f"Tool completion status sent to frontend: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to send tool completion status to frontend: {e}")
        
        logger.info(f"Tool response received: {tool_name} (ID: {response_id})")
    
    def _format_tool_response(self, response_data: Any) -> str:
        """Format tool response data"""
        if response_data is None:
            return ""
        
        if isinstance(response_data, dict):
            try:
                return json.dumps(response_data, indent=2, ensure_ascii=False)
            except:
                return str(response_data)
        elif isinstance(response_data, (list, tuple)):
            try:
                return json.dumps(response_data, indent=2, ensure_ascii=False)
            except:
                return str(response_data)
        elif isinstance(response_data, str):
            return response_data
        else:
            return str(response_data)
    
    def _extract_final_response(self, events: List[Any]) -> str:
        """Extract final response from events"""
        # Look for the last valid response
        for event in reversed(events):
            if hasattr(event, 'content') and event.content:
                content = event.content
                if hasattr(content, 'parts') and content.parts:
                    text_parts = []
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    if text_parts:
                        return '\n'.join(text_parts)
                elif hasattr(content, 'text') and content.text:
                    return content.text
            elif hasattr(event, 'text') and event.text:
                return event.text
            elif hasattr(event, 'output') and event.output:
                return event.output
            elif hasattr(event, 'message') and event.message:
                return event.message
        
        return "No response generated"
    
    def _extract_usage_metadata(self, events: List[Any]) -> Dict[str, int]:
        """Extract token usage metadata from events - 参考原始代码的token提取逻辑"""
        usage_metadata = {
            'prompt_tokens': 0,
            'candidates_tokens': 0,
            'total_tokens': 0
        }
        
        for event in events:
            # logger.info(event)
            # 检查事件是否有 usage_metadata 属性
            if hasattr(event, 'usage_metadata') and event.usage_metadata:
                if hasattr(event, 'author') and event.author != "Question_Answer_Agent":
                # logger.info(f"Found usage_metadata in event: {event.usage_metadata}")
                    usage_metadata['prompt_tokens'] += getattr(event.usage_metadata, 'prompt_token_count', 0)
                    usage_metadata['candidates_tokens'] += getattr(event.usage_metadata, 'candidates_token_count', 0)
                    usage_metadata['total_tokens'] += getattr(event.usage_metadata, 'total_token_count', 0)
        
        return usage_metadata
    
    async def _process_photon_charging(self, 
                                     usage_metadata: Dict[str, int], 
                                     tool_calls: List[Dict], 
                                     context: EventContext) -> Optional[Dict[str, Any]]:
        """处理光子扣费 - 参考原始代码的收费逻辑"""
        photon_service = get_photon_service()
        if not photon_service:
            logger.warning("光子服务未初始化，跳过收费")
            return None
        
        try:
            # 获取输入输出token数量
            input_tokens = usage_metadata.get('prompt_tokens', 0)
            output_tokens = usage_metadata.get('candidates_tokens', 0)
            
            # 计算工具调用次数（从当前会话的工具调用中统计）
            tool_call_count = len(tool_calls)
            
            # 如果从消息历史中统计工具调用次数（参考原始代码）
            if context.session_id in self.message_history:
                # 统计当前会话中最后一次用户消息后的工具调用次数
                for msg in reversed(self.message_history[context.session_id]):
                    if isinstance(msg, UserMessage):
                        break
                    if isinstance(msg, ToolMessage):
                        tool_call_count += 1
            
            if input_tokens > 0 or output_tokens > 0 or tool_call_count > 0:
                logger.info(f"Processing photon charge - Input tokens: {input_tokens}, Output tokens: {output_tokens}, Tool calls: {tool_call_count}")
                
                # 执行收费
                charge_result = await photon_service.charge_photon(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    tool_calls=tool_call_count,
                    request=None,  # WebSocket 连接中无法直接获取 Request 对象
                    context=context  # 传递事件上下文
                )
                
                # 格式化收费结果
                result = {
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
                
                return result
            else:
                logger.info("No tokens or tool calls to charge")
                return None
                
        except Exception as e:
            logger.error(f"Error during photon charging: {e}")
            return {
                "success": False,
                "code": -1,
                "message": f"收费过程中发生错误: {str(e)}",
                "biz_no": None,
                "photon_amount": 0,
                "rmb_amount": 0.0
            }
    
    def get_message_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get message history for a session"""
        if session_id not in self.message_history:
            logger.warning(f"会话 {session_id} 没有消息历史")
            return []
        
        messages = self.message_history[session_id]
        logger.info(f"获取会话 {session_id} 的消息历史，共 {len(messages)} 条消息")
        
        # 转换为前端期望的格式
        formatted_messages = []
        for msg in messages:
            try:
                # 根据消息类型转换为前端期望的格式
                if isinstance(msg, UserMessage):
                    formatted_msg = {
                        "id": msg.id,
                        "role": "user",
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "session_id": msg.session_id
                    }
                elif isinstance(msg, AssistantMessage):
                    formatted_msg = {
                        "id": msg.id,
                        "role": "assistant",
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "session_id": msg.session_id,
                        "tool_calls": msg.tool_calls
                    }
                elif isinstance(msg, ToolMessage):
                    # 处理工具消息
                    if msg.tool_status == MessageStatus.PROCESSING:
                        # 工具执行中
                        formatted_msg = {
                            "id": msg.id,
                            "role": "tool",
                            "content": msg.content,
                            "timestamp": msg.timestamp.isoformat(),
                            "session_id": msg.session_id,
                            "tool_name": msg.tool_name,
                            "tool_status": msg.tool_status.value,
                            "is_long_running": msg.is_long_running
                        }
                    else:
                        # 工具执行完成
                        formatted_msg = {
                            "id": msg.id,
                            "role": "tool",
                            "content": msg.content,
                            "timestamp": msg.timestamp.isoformat(),
                            "session_id": msg.session_id,
                            "tool_name": msg.tool_name,
                            "tool_status": msg.tool_status.value,
                            "result": msg.result
                        }
                else:
                    # 其他类型的消息
                    formatted_msg = msg.to_dict()
                
                formatted_messages.append(formatted_msg)
                logger.debug(f"格式化消息: {formatted_msg['role']} - {formatted_msg['content'][:30]}...")
                
            except Exception as e:
                logger.error(f"格式化消息失败: {e}, 消息: {msg}")
                continue
        
        logger.info(f"会话 {session_id} 格式化完成，共 {len(formatted_messages)} 条消息")
        return formatted_messages
    
    def clear_message_history(self, session_id: str):
        """Clear message history for a session"""
        if session_id in self.message_history:
            del self.message_history[session_id]
    
    def get_message_count(self, session_id: str) -> int:
        """Get message count for a session"""
        return len(self.message_history.get(session_id, []))
    
    def create_system_message(self, content: str, level: str = "info", code: Optional[str] = None) -> SystemMessage:
        """Create a system message"""
        return SystemMessage(
            content=content,
            level=level,
            code=code
        )