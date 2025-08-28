"""
Event handlers for different types of events
"""

from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime
import logging
import json
from .message_types import MessageType, EventType, Message, ToolMessage
from .state_machine import SessionState

logger = logging.getLogger(__name__)


@dataclass
class EventContext:
    """Context for event processing"""
    session_id: str
    user_id: str
    message_id: str
    timestamp: datetime
    metadata: Dict[str, Any]


class EventHandler:
    """Base event handler class"""
    
    def __init__(self):
        self.handlers: Dict[EventType, List[Callable]] = {}
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default event handlers"""
        pass
    
    def register_handler(self, event_type: EventType, handler: Callable):
        """Register a handler for an event type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def unregister_handler(self, event_type: EventType, handler: Callable):
        """Unregister a handler for an event type"""
        if event_type in self.handlers:
            try:
                self.handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    async def handle_event(self, event_type: EventType, context: EventContext, data: Any):
        """Handle an event of the specified type"""
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    await handler(context, data)
                except Exception as e:
                    logger.error(f"Error in event handler {handler.__name__}: {e}")
    
    def get_handler_count(self, event_type: EventType) -> int:
        """Get the number of handlers for an event type"""
        return len(self.handlers.get(event_type, []))


class ToolEventProcessor:
    """Process tool-related events"""
    
    def __init__(self):
        self.active_tools: Dict[str, Dict[str, Any]] = {}
        self.tool_results: Dict[str, Any] = {}
    
    async def process_tool_call_started(self, context: EventContext, data: Dict[str, Any]):
        """Process tool call started event"""
        tool_id = data.get('tool_id', data.get('name', 'unknown'))
        tool_name = data.get('name', 'unknown')
        
        self.active_tools[tool_id] = {
            'name': tool_name,
            'started_at': context.timestamp,
            'session_id': context.session_id,
            'user_id': context.user_id,
            'status': 'executing'
        }
        
        logger.info(f"Tool call started: {tool_name} (ID: {tool_id})")
    
    async def process_tool_call_completed(self, context: EventContext, data: Dict[str, Any]):
        """Process tool call completed event"""
        tool_id = data.get('tool_id', data.get('name', 'unknown'))
        tool_name = data.get('name', 'unknown')
        result = data.get('result')
        error = data.get('error')
        
        if tool_id in self.active_tools:
            tool_info = self.active_tools[tool_id]
            tool_info['completed_at'] = context.timestamp
            tool_info['status'] = 'completed' if not error else 'failed'
            tool_info['result'] = result
            tool_info['error'] = error
            
            # Store result
            self.tool_results[tool_id] = {
                'name': tool_name,
                'result': result,
                'error': error,
                'duration': (context.timestamp - tool_info['started_at']).total_seconds()
            }
            
            logger.info(f"Tool call completed: {tool_name} (ID: {tool_id})")
    
    async def process_tool_call_failed(self, context: EventContext, data: Dict[str, Any]):
        """Process tool call failed event"""
        tool_id = data.get('tool_id', data.get('name', 'unknown'))
        tool_name = data.get('name', 'unknown')
        error = data.get('error', 'Unknown error')
        
        if tool_id in self.active_tools:
            tool_info = self.active_tools[tool_id]
            tool_info['completed_at'] = context.timestamp
            tool_info['status'] = 'failed'
            tool_info['error'] = error
            
            logger.error(f"Tool call failed: {tool_name} (ID: {tool_id}): {error}")
    
    def get_active_tools(self, session_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get active tools, optionally filtered by session"""
        if session_id:
            return {
                tool_id: tool_info for tool_id, tool_info in self.active_tools.items()
                if tool_info.get('session_id') == session_id
            }
        return self.active_tools.copy()
    
    def get_tool_result(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get result for a specific tool"""
        return self.tool_results.get(tool_id)
    
    def cleanup_completed_tools(self, max_age_seconds: int = 3600):
        """Clean up completed tools older than specified age"""
        current_time = datetime.now()
        to_remove = []
        
        for tool_id, tool_info in self.active_tools.items():
            if 'completed_at' in tool_info:
                age = (current_time - tool_info['completed_at']).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(tool_id)
        
        for tool_id in to_remove:
            del self.active_tools[tool_id]
            if tool_id in self.tool_results:
                del self.tool_results[tool_id]


class MessageEventProcessor:
    """Process message-related events"""
    
    def __init__(self):
        self.message_queue: List[Dict[str, Any]] = []
        self.processing_messages: Dict[str, Dict[str, Any]] = {}
    
    async def process_message_received(self, context: EventContext, data: Dict[str, Any]):
        """Process message received event"""
        message_info = {
            'id': context.message_id,
            'session_id': context.session_id,
            'user_id': context.user_id,
            'timestamp': context.timestamp,
            'content': data.get('content', ''),
            'type': data.get('type', 'unknown'),
            'status': 'received'
        }
        
        self.message_queue.append(message_info)
        logger.info(f"Message received: {context.message_id}")
    
    async def process_message_processing(self, context: EventContext, data: Dict[str, Any]):
        """Process message processing event"""
        message_id = context.message_id
        
        if message_id in self.processing_messages:
            self.processing_messages[message_id]['status'] = 'processing'
            self.processing_messages[message_id]['processing_started'] = context.timestamp
        else:
            self.processing_messages[message_id] = {
                'id': message_id,
                'session_id': context.session_id,
                'user_id': context.user_id,
                'timestamp': context.timestamp,
                'status': 'processing',
                'processing_started': context.timestamp
            }
        
        logger.info(f"Message processing started: {message_id}")
    
    async def process_message_completed(self, context: EventContext, data: Dict[str, Any]):
        """Process message completed event"""
        message_id = context.message_id
        
        if message_id in self.processing_messages:
            self.processing_messages[message_id]['status'] = 'completed'
            self.processing_messages[message_id]['completed_at'] = context.timestamp
            
            # Calculate processing time
            started = self.processing_messages[message_id].get('processing_started')
            if started:
                duration = (context.timestamp - started).total_seconds()
                self.processing_messages[message_id]['processing_duration'] = duration
            
            logger.info(f"Message completed: {message_id}")
    
    async def process_message_failed(self, context: EventContext, data: Dict[str, Any]):
        """Process message failed event"""
        message_id = context.message_id
        error = data.get('error', 'Unknown error')
        
        if message_id in self.processing_messages:
            self.processing_messages[message_id]['status'] = 'failed'
            self.processing_messages[message_id]['error'] = error
            self.processing_messages[message_id]['failed_at'] = context.timestamp
            
            logger.error(f"Message failed: {message_id}: {error}")
    
    def get_message_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get status for a specific message"""
        return self.processing_messages.get(message_id)
    
    def get_queue_length(self) -> int:
        """Get current message queue length"""
        return len(self.message_queue)
    
    def get_processing_messages(self, session_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get processing messages, optionally filtered by session"""
        if session_id:
            return {
                msg_id: msg_info for msg_id, msg_info in self.processing_messages.items()
                if msg_info.get('session_id') == session_id
            }
        return self.processing_messages.copy()


class EventProcessor:
    """Main event processor that coordinates all event handlers"""
    
    def __init__(self):
        self.tool_processor = ToolEventProcessor()
        self.message_processor = MessageEventProcessor()
        self.custom_handlers: Dict[EventType, List[Callable]] = {}
    
    async def process_event(self, event_type: EventType, context: EventContext, data: Any):
        """Process an event using appropriate processor"""
        try:
            # Process tool events
            if event_type == EventType.TOOL_CALL_STARTED:
                await self.tool_processor.process_tool_call_started(context, data)
            elif event_type == EventType.TOOL_CALL_COMPLETED:
                await self.tool_processor.process_tool_call_completed(context, data)
            elif event_type == EventType.TOOL_CALL_FAILED:
                await self.tool_processor.process_tool_call_failed(context, data)
            
            # Process message events
            elif event_type == EventType.RESPONSE_GENERATED:
                await self.message_processor.process_message_completed(context, data)
            elif event_type == EventType.ERROR_OCCURRED:
                await self.message_processor.process_message_failed(context, data)
            
            # Process custom handlers
            if event_type in self.custom_handlers:
                for handler in self.custom_handlers[event_type]:
                    try:
                        await handler(context, data)
                    except Exception as e:
                        logger.error(f"Error in custom event handler: {e}")
            
            logger.debug(f"Event processed: {event_type.value}")
            
        except Exception as e:
            logger.error(f"Error processing event {event_type.value}: {e}")
    
    def register_custom_handler(self, event_type: EventType, handler: Callable):
        """Register a custom event handler"""
        if event_type not in self.custom_handlers:
            self.custom_handlers[event_type] = []
        self.custom_handlers[event_type].append(handler)
    
    def get_tool_processor(self) -> ToolEventProcessor:
        """Get the tool event processor"""
        return self.tool_processor
    
    def get_message_processor(self) -> MessageEventProcessor:
        """Get the message event processor"""
        return self.message_processor 