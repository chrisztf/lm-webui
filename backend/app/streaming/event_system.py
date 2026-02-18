from enum import Enum
from typing import Callable, List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import time
import json
import logging

logger = logging.getLogger(__name__)

class EventType(Enum):
    """All streaming event types"""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    TOKEN_RECEIVED = "token_received"
    TOKEN_BATCH = "token_batch"
    TEXT_CHUNK = "text_chunk"
    TEXT_COMPLETE = "text_complete"
    FINAL_ANSWER = "final_answer"
    REASONING_START = "reasoning_start"
    REASONING_STEP = "reasoning_step"
    REASONING_END = "reasoning_end"
    SEARCH_START = "search_start"
    SEARCH_RESULT = "search_result"
    CODE_EXECUTION = "code_execution"
    CODE_RESULT = "code_result"
    CALCULATION = "calculation"
    CALCULATION_RESULT = "calculation_result"
    SEARCH_END = "search_end"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    CANCELLED = "cancelled"

@dataclass
class StreamingEvent:
    """Base streaming event"""
    type: EventType
    session_id: str
    timestamp: float
    data: Any
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata or {},
        }

class EventHandler:
    """Base event handler"""
    
    def can_handle(self, event: StreamingEvent) -> bool:
        raise NotImplementedError
    
    async def handle(self, event: StreamingEvent) -> None:
        raise NotImplementedError

class EventDispatcher:
    """Routes events to appropriate handlers"""
    
    def __init__(self):
        self.handlers: Dict[EventType, List[EventHandler]] = {}
    
    def register(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    async def dispatch(self, event: StreamingEvent) -> None:
        handlers = self.handlers.get(event.type, [])
        for handler in handlers:
            if handler.can_handle(event):
                try:
                    await handler.handle(event)
                except Exception as e:
                    logger.error(f"Error in handler {handler.__class__.__name__}: {str(e)}")

class EventEmitter:
    """Emits events to listeners (e.g. WebSocket)"""
    
    def __init__(self):
        self.listeners: List[Callable] = []
    
    def on(self, callback: Callable) -> None:
        if callback not in self.listeners:
            self.listeners.append(callback)
    
    async def emit(self, event: StreamingEvent) -> None:
        for listener in self.listeners:
            try:
                await listener(event)
            except Exception as e:
                logger.error(f"Error in event listener: {str(e)}")
