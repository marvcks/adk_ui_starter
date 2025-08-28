"""
Message type definitions for WebSocket communication
"""

from enum import Enum
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class MessageType(Enum):
    """Message types for WebSocket communication"""
    # User messages
    USER_MESSAGE = "user_message"
    
    # Assistant responses
    ASSISTANT_RESPONSE = "assistant_response"
    ASSISTANT_STREAMING = "assistant_streaming"
    
    # Tool related
    TOOL_CALL = "tool_call"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    TOOL_ERROR = "tool_error"
    
    # Session management
    SESSION_CREATED = "session_created"
    SESSION_SWITCHED = "session_switched"
    SESSION_DELETED = "session_deleted"
    SESSIONS_LIST = "sessions_list"
    SESSION_MESSAGES = "session_messages"
    
    # System messages
    SYSTEM_INFO = "system_info"
    SYSTEM_ERROR = "system_error"
    SYSTEM_WARNING = "system_warning"
    
    # Status messages
    STATUS_UPDATE = "status_update"
    COMPLETE = "complete"
    
    # Shell related
    SHELL_COMMAND = "shell_command"
    SHELL_OUTPUT = "shell_output"
    SHELL_ERROR = "shell_error"
    
    # File related
    FILE_UPDATE = "file_update"
    FILE_TREE = "file_tree"


class MessageStatus(Enum):
    """Message status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EventType(Enum):
    """Event types for agent execution"""
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"
    RESPONSE_GENERATED = "response_generated"
    SESSION_UPDATED = "session_updated"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class Message:
    """Base message class"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.USER_MESSAGE
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    status: MessageStatus = MessageStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "metadata": self.metadata
        }


@dataclass
class UserMessage(Message):
    """User message"""
    type: MessageType = MessageType.USER_MESSAGE
    session_id: Optional[str] = None


@dataclass
class AssistantMessage(Message):
    """Assistant response message"""
    type: MessageType = MessageType.ASSISTANT_RESPONSE
    session_id: Optional[str] = None
    is_streaming: bool = False
    tool_calls: list = field(default_factory=list)


@dataclass
class ToolMessage(Message):
    """Tool execution message - 参考 ADK Web 实现"""
    type: MessageType = MessageType.TOOL_CALL
    tool_name: str = ""
    tool_id: Optional[str] = None
    tool_status: MessageStatus = MessageStatus.PENDING
    is_long_running: bool = False
    result: Optional[str] = None
    error: Optional[str] = None
    session_id: Optional[str] = None  # 添加 session_id 支持，参考 ADK Web
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool message to dictionary - 参考 ADK Web 格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "tool_name": self.tool_name,
            "tool_id": self.tool_id,
            "tool_status": self.tool_status.value,
            "is_long_running": self.is_long_running,
            "result": self.result,
            "error": self.error,
            "session_id": self.session_id  # 包含 session_id
        })
        return base_dict


@dataclass
class SessionMessage(Message):
    """Session management message"""
    type: MessageType = MessageType.SESSION_CREATED
    session_id: str = ""
    session_data: Optional[Dict[str, Any]] = None


@dataclass
class SystemMessage(Message):
    """System message"""
    type: MessageType = MessageType.SYSTEM_INFO
    level: str = "info"  # info, warning, error
    code: Optional[str] = None


@dataclass
class WebSocketMessage:
    """WebSocket message wrapper"""
    type: str
    data: Dict[str, Any]
    id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for WebSocket transmission"""
        return {
            "type": self.type,
            "data": self.data,
            "id": self.id or str(uuid.uuid4()),
            "timestamp": self.timestamp.isoformat()
        }


def create_message(message_type: MessageType, **kwargs) -> Message:
    """Factory function to create messages"""
    message_classes = {
        MessageType.USER_MESSAGE: UserMessage,
        MessageType.ASSISTANT_RESPONSE: AssistantMessage,
        MessageType.TOOL_CALL: ToolMessage,
        MessageType.SESSION_CREATED: SessionMessage,
        MessageType.SYSTEM_INFO: SystemMessage,
    }
    
    message_class = message_classes.get(message_type, Message)
    return message_class(type=message_type, **kwargs)


def validate_message(message_data: Dict[str, Any]) -> bool:
    """Validate message data"""
    required_fields = ["type", "content"]
    return all(field in message_data for field in required_fields)


def parse_message(message_data: Dict[str, Any]) -> Optional[Message]:
    """Parse message data into Message object"""
    if not validate_message(message_data):
        return None
    
    try:
        message_type = MessageType(message_data["type"])
        return create_message(message_type, **message_data)
    except (ValueError, KeyError):
        return None 