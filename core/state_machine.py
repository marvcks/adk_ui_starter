"""
State machine for session and message management
"""

from enum import Enum
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session states"""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    WAITING_FOR_TOOL = "waiting_for_tool"
    ERROR = "error"
    CLOSED = "closed"


class MessageState(Enum):
    """Message processing states"""
    RECEIVED = "received"
    VALIDATING = "validating"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StateTransition:
    """State transition definition"""
    from_state: SessionState
    to_state: SessionState
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    action: Optional[Callable[[Dict[str, Any]], None]] = None
    description: str = ""


class StateMachine:
    """State machine for managing session states"""
    
    def __init__(self, initial_state: SessionState = SessionState.INITIALIZING):
        self.current_state = initial_state
        self.state_history: list[tuple[SessionState, datetime, str]] = []
        self.transitions: list[StateTransition] = []
        self.state_data: Dict[str, Any] = {}
        self._setup_default_transitions()
    
    def _setup_default_transitions(self):
        """Setup default state transitions"""
        self.add_transition(
            SessionState.INITIALIZING,
            SessionState.READY,
            description="Session initialization completed"
        )
        
        self.add_transition(
            SessionState.READY,
            SessionState.PROCESSING,
            description="Message processing started"
        )
        
        self.add_transition(
            SessionState.PROCESSING,
            SessionState.WAITING_FOR_TOOL,
            description="Tool execution started"
        )
        
        self.add_transition(
            SessionState.WAITING_FOR_TOOL,
            SessionState.PROCESSING,
            description="Tool execution completed"
        )
        
        self.add_transition(
            SessionState.PROCESSING,
            SessionState.READY,
            description="Message processing completed"
        )
        
        self.add_transition(
            SessionState.PROCESSING,
            SessionState.ERROR,
            description="Error occurred during processing"
        )
        
        self.add_transition(
            SessionState.ERROR,
            SessionState.READY,
            description="Error recovered, returning to ready state"
        )
        
        self.add_transition(
            SessionState.READY,
            SessionState.CLOSED,
            description="Session closed"
        )
    
    def add_transition(self, from_state: SessionState, to_state: SessionState, 
                      condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
                      action: Optional[Callable[[Dict[str, Any]], None]] = None,
                      description: str = ""):
        """Add a new state transition"""
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            condition=condition,
            action=action,
            description=description
        )
        self.transitions.append(transition)
    
    def can_transition_to(self, target_state: SessionState, context: Dict[str, Any] = None) -> bool:
        """Check if transition to target state is allowed"""
        context = context or {}
        
        for transition in self.transitions:
            if (transition.from_state == self.current_state and 
                transition.to_state == target_state):
                
                # Check condition if specified
                if transition.condition:
                    try:
                        return transition.condition(context)
                    except Exception as e:
                        logger.error(f"Error checking transition condition: {e}")
                        return False
                return True
        
        return False
    
    def transition_to(self, target_state: SessionState, context: Dict[str, Any] = None, 
                     reason: str = "") -> bool:
        """Attempt to transition to target state"""
        context = context or {}
        
        if not self.can_transition_to(target_state, context):
            logger.warning(f"Cannot transition from {self.current_state} to {target_state}")
            return False
        
        # Find the transition
        transition = None
        for t in self.transitions:
            if t.from_state == self.current_state and t.to_state == target_state:
                transition = t
                break
        
        if not transition:
            return False
        
        # Execute action if specified
        if transition.action:
            try:
                transition.action(context)
            except Exception as e:
                logger.error(f"Error executing transition action: {e}")
                return False
        
        # Record state change
        old_state = self.current_state
        self.current_state = target_state
        self.state_history.append((old_state, datetime.now(), reason or transition.description))
        
        logger.info(f"State transition: {old_state} -> {target_state} ({reason or transition.description})")
        return True
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get current state information"""
        return {
            "current_state": self.current_state.value,
            "state_data": self.state_data.copy(),
            "state_history": [
                {
                    "state": state.value,
                    "timestamp": timestamp.isoformat(),
                    "reason": reason
                }
                for state, timestamp, reason in self.state_history
            ]
        }
    
    def set_state_data(self, key: str, value: Any):
        """Set state data"""
        self.state_data[key] = value
    
    def get_state_data(self, key: str, default: Any = None) -> Any:
        """Get state data"""
        return self.state_data.get(key, default)
    
    def is_in_state(self, state: SessionState) -> bool:
        """Check if currently in specified state"""
        return self.current_state == state
    
    def reset_to_state(self, state: SessionState, reason: str = "Manual reset"):
        """Reset to specified state (for error recovery)"""
        if state in [SessionState.READY, SessionState.INITIALIZING]:
            self.current_state = state
            self.state_history.append((self.current_state, datetime.now(), reason))
            self.state_data.clear()
            logger.info(f"State reset to {state}: {reason}")
            return True
        return False


class SessionStateManager:
    """Manager for multiple session state machines"""
    
    def __init__(self):
        self.sessions: Dict[str, StateMachine] = {}
    
    def create_session(self, session_id: str) -> StateMachine:
        """Create a new session state machine"""
        state_machine = StateMachine(SessionState.INITIALIZING)
        self.sessions[session_id] = state_machine
        return state_machine
    
    def get_session(self, session_id: str) -> Optional[StateMachine]:
        """Get session state machine"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """Remove session state machine"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_all_sessions(self) -> Dict[str, StateMachine]:
        """Get all session state machines"""
        return self.sessions.copy()
    
    def get_sessions_by_state(self, state: SessionState) -> list[str]:
        """Get session IDs that are in specified state"""
        return [
            session_id for session_id, sm in self.sessions.items()
            if sm.is_in_state(state)
        ] 