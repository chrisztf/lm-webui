"""
Streaming Event Definitions

Defines the event types and structures used for real-time communication
between backend and frontend during streaming chats.
"""
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import json


class EventType(str, Enum):
    """Types of streaming events"""

    # Session control
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # Search functionality
    SEARCH_START = "search_start"
    SEARCH_RESULT = "search_result"
    SEARCH_END = "search_end"

    # Status indicators (for DeepSeek/Gemini/Claude style UI)
    STATUS_SEARCHING = "status_searching"
    STATUS_ANALYZING = "status_analyzing"
    STATUS_ENHANCING = "status_enhancing"
    STATUS_THINKING = "status_thinking"
    STATUS_COMPLETE = "status_complete"

    # Code execution
    CODE_EXECUTION = "code_execution"
    CODE_RESULT = "code_result"

    # Mathematics
    CALCULATION = "calculation"
    CALCULATION_RESULT = "calculation_result"

    # Text content
    TEXT_CHUNK = "text_chunk"
    TEXT_COMPLETE = "text_complete"

    # Final answer
    FINAL_ANSWER = "final_answer"

    # Control events
    CANCELLED = "cancelled"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class StreamingEvent(BaseModel):
    """Base streaming event structure"""

    type: EventType
    content: str
    timestamp: int
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    step_index: Optional[int] = None

    def to_json(self) -> str:
        """Export event as JSON string"""
        return json.dumps(self.dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "StreamingEvent":
        """Create event from JSON string"""
        data = json.loads(json_str)
        return cls(**data)

    @staticmethod
    def _get_timestamp() -> int:
        """Get current timestamp in milliseconds"""
        import time
        return int(time.time() * 1000)


class SearchEvent(StreamingEvent):
    """Search-related event structure"""

    def __init__(
        self,
        event_type: EventType,
        query: str,
        results: Optional[List[Dict[str, Any]]] = None,
        url: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        content = query
        if event_type == EventType.SEARCH_RESULT and results:
            content = results[0].get("title", query) if results else query

        metadata = {
            "query": query,
            "results_count": len(results) if results else 0
        }

        if results:
            metadata["results"] = results
        if url:
            metadata["url"] = url

        super().__init__(
            type=event_type,
            content=content,
            timestamp=self._get_timestamp(),
            session_id=session_id,
            metadata=metadata
        )


class CodeEvent(StreamingEvent):
    """Code execution event structure"""

    def __init__(
        self,
        event_type: EventType,
        code: str,
        language: str = "python",
        output: Optional[str] = None,
        error: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        content = output if event_type == EventType.CODE_RESULT and output else code

        metadata = {
            "code": code,
            "language": language
        }

        if output:
            metadata["output"] = output
        if error:
            metadata["error"] = error

        super().__init__(
            type=event_type,
            content=content,
            timestamp=self._get_timestamp(),
            session_id=session_id,
            metadata=metadata
        )


class CalculationEvent(StreamingEvent):
    """Mathematical calculation event structure"""

    def __init__(
        self,
        event_type: EventType,
        expression: str,
        result: Optional[str] = None,
        steps: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ):
        content = result if event_type == EventType.CALCULATION_RESULT and result else expression

        metadata = {
            "expression": expression
        }

        if result:
            metadata["result"] = result
        if steps:
            metadata["steps"] = steps

        super().__init__(
            type=event_type,
            content=content,
            timestamp=self._get_timestamp(),
            session_id=session_id,
            metadata=metadata
        )


class TextEvent(StreamingEvent):
    """Text content event structure"""

    def __init__(
        self,
        content: str,
        is_complete: bool = False,
        word_count: Optional[int] = None,
        session_id: Optional[str] = None
    ):
        super().__init__(
            type=EventType.TEXT_COMPLETE if is_complete else EventType.TEXT_CHUNK,
            content=content,
            timestamp=self._get_timestamp(),
            session_id=session_id,
            metadata={
                "word_count": word_count or len(content.split()),
                "char_count": len(content),
                "is_complete": is_complete
            }
        )


# Event factory functions for easy creation
def create_session_start_event(session_id: str, metadata: Optional[Dict[str, Any]] = None) -> StreamingEvent:
    """Create session start event"""
    return StreamingEvent(
        type=EventType.SESSION_START,
        content="Session started - beginning reasoning process",
        timestamp=StreamingEvent._get_timestamp(),
        session_id=session_id,
        metadata=metadata or {}
    )


def create_final_answer_event(content: str, session_id: Optional[str] = None) -> StreamingEvent:
    """Create final answer event"""
    return StreamingEvent(
        type=EventType.FINAL_ANSWER,
        content=content,
        timestamp=StreamingEvent._get_timestamp(),
        session_id=session_id
    )


def create_error_event(error_message: str, session_id: Optional[str] = None) -> StreamingEvent:
    """Create error event"""
    return StreamingEvent(
        type=EventType.ERROR,
        content=error_message,
        timestamp=StreamingEvent._get_timestamp(),
        session_id=session_id
    )


def create_cancelled_event(session_id: Optional[str] = None) -> StreamingEvent:
    """Create cancellation event"""
    return StreamingEvent(
        type=EventType.CANCELLED,
        content="Reasoning cancelled by user",
        timestamp=StreamingEvent._get_timestamp(),
        session_id=session_id
    )


def create_heartbeat_event(session_id: str) -> StreamingEvent:
    """Create heartbeat event for connection health"""
    return StreamingEvent(
        type=EventType.HEARTBEAT,
        content="ping",
        timestamp=StreamingEvent._get_timestamp(),
        session_id=session_id
    )


def create_status_searching_event(session_id: str, query: Optional[str] = None) -> StreamingEvent:
    """Create searching status event"""
    return StreamingEvent(
        type=EventType.STATUS_SEARCHING,
        content="Searching for information...",
        timestamp=StreamingEvent._get_timestamp(),
        session_id=session_id,
        metadata={"query": query} if query else None
    )


def create_status_analyzing_event(session_id: str, analysis_type: str = "general") -> StreamingEvent:
    """Create analyzing status event"""
    return StreamingEvent(
        type=EventType.STATUS_ANALYZING,
        content="Analyzing information...",
        timestamp=StreamingEvent._get_timestamp(),
        session_id=session_id,
        metadata={"analysis_type": analysis_type}
    )


def create_status_enhancing_event(session_id: str) -> StreamingEvent:
    """Create enhancing status event"""
    return StreamingEvent(
        type=EventType.STATUS_ENHANCING,
        content="Enhancing answer...",
        timestamp=StreamingEvent._get_timestamp(),
        session_id=session_id
    )




# Event parsing utilities
def parse_reasoning_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Parse structured reasoning from model output text

    Expected formats in text:
    {reasoning_step: "Step 1: Analyzing problem", type: "inference"}
    {search: "quantum physics", query: "..."}
    {calculation: "2+2", result: "4"}
    {code: "print('hello')", result: "hello"}
    """
    import re
    import json

    reasoning_events = []

    # Find all JSON-like objects in the text
    # This is a simple regex pattern for {...} blocks
    json_pattern = r'\{[^}]*\}'
    matches = re.finditer(json_pattern, text)

    for match in matches:
        json_str = match.group()
        try:
            data = json.loads(json_str)

            if "reasoning_step" in data:
                reasoning_events.append({
                    "type": "reasoning_step",
                    "content": data["reasoning_step"],
                    "metadata": {
                        "step_type": data.get("type", "inference"),
                        "title": data.get("title", f"Reasoning Step")
                    }
                })
            elif "search" in data:
                reasoning_events.append({
                    "type": "search_start",
                    "content": data["search"],
                    "metadata": {"query": data.get("query", data["search"])}
                })
            elif "calculation" in data:
                reasoning_events.append({
                    "type": EventType.CALCULATION.value,
                    "content": data["calculation"],
                    "metadata": {
                        "expression": data["calculation"],
                        "result": data.get("result")
                    }
                })
            elif "code" in data:
                reasoning_events.append({
                    "type": EventType.CODE_EXECUTION.value,
                    "content": data["code"],
                    "metadata": {
                        "code": data["code"],
                        "language": data.get("language", "python"),
                        "output": data.get("result")
                    }
                })

        except json.JSONDecodeError:
            # Not valid JSON, skip
            continue

    return reasoning_events


# Export convenience imports
__all__ = [
    "EventType",
    "StreamingEvent",
    "SearchEvent",
    "CodeEvent",
    "CalculationEvent",
    "TextEvent",
    # Factory functions
    "create_session_start_event",
    "create_final_answer_event",
    "create_error_event",
    "create_cancelled_event",
    "create_heartbeat_event",
    # Utilities
    "parse_reasoning_from_text"
]
