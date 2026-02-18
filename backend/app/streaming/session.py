"""
Streaming Session Manager

Handles the lifecycle of streaming chat sessions, including:
- Session creation and tracking
- Cancellation handling
- Resource cleanup
- Session state management
"""
import asyncio
import uuid
from typing import Dict, Any, Optional, AsyncGenerator, List, Callable
from datetime import datetime, timedelta
from .event_system import EventDispatcher, EventEmitter, StreamingEvent, EventType
from .handlers import TokenHandler, SearchHandler, CodeHandler, ErrorHandler


class StreamingSession:
    """Represents a single streaming chat session"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.is_cancelled = False
        self.is_active = True
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.metadata: Dict[str, Any] = {}

    def cancel(self):
        """Cancel the session and all active tasks"""
        self.is_cancelled = True
        self.is_active = False

        # Cancel all active tasks
        for task_id, task in self.active_tasks.items():
            if not task.done():
                task.cancel()

        self.active_tasks.clear()

    def add_task(self, task_id: str, task: asyncio.Task):
        """Add an active task to the session"""
        self.active_tasks[task_id] = task

    def remove_task(self, task_id: str):
        """Remove a completed task from the session"""
        self.active_tasks.pop(task_id, None)

    def is_expired(self, max_age_seconds: int = 3600) -> bool:
        """Check if session has exceeded maximum age"""
        return (datetime.now() - self.created_at).seconds > max_age_seconds


class StreamingManager:
    """Manages all active streaming sessions with event dispatching"""

    def __init__(self):
        self.sessions: Dict[str, StreamingSession] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        self.dispatcher = EventDispatcher()
        self.emitter = EventEmitter()
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register default event handlers"""
        self.dispatcher.register(EventType.TOKEN_RECEIVED, TokenHandler())
        self.dispatcher.register(EventType.SEARCH_START, SearchHandler())
        self.dispatcher.register(EventType.CODE_EXECUTION, CodeHandler())
        self.dispatcher.register(EventType.ERROR, ErrorHandler())

    async def emit_event(self, event: StreamingEvent) -> None:
        """Process event through dispatcher and emitter"""
        await self.dispatcher.dispatch(event)
        await self.emitter.emit(event)

    def on_event(self, callback: Callable) -> None:
        """Register a global event listener (e.g. for WebSocket)"""
        self.emitter.on(callback)

    def create_session(self) -> str:
        """Create a new streaming session and return its ID"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = StreamingSession(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[StreamingSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)

    def cancel_session(self, session_id: str) -> bool:
        """Cancel a session by ID"""
        session = self.get_session(session_id)
        if session:
            session.cancel()
            return True
        return False

    def cleanup_session(self, session_id: str):
        """Remove a session from memory"""
        self.sessions.pop(session_id, None)

    def clear_all_sessions(self):
        """Cancel and remove all sessions (useful for shutdown/startup)"""
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            self.cancel_session(session_id)
            self.cleanup_session(session_id)
        print(f"🧹 Cleared all {len(session_ids)} active sessions")

    def is_session_cancelled(self, session_id: str) -> bool:
        """Check if a session has been cancelled"""
        session = self.get_session(session_id)
        return session.is_cancelled if session else True

    def list_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active sessions with basic info"""
        return {
            session_id: {
                "created_at": session.created_at.isoformat(),
                "is_cancelled": session.is_cancelled,
                "active_tasks": len(session.active_tasks),
                "age_seconds": int((datetime.now() - session.created_at).total_seconds())
            }
            for session_id, session in self.sessions.items()
            if session.is_active
        }

    async def start_background_cleanup(self):
        """Start background task to clean up expired sessions"""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())

    async def _cleanup_expired_sessions(self):
        """Periodically clean up expired sessions"""
        while True:
            await asyncio.sleep(300)  # Check every 5 minutes

            expired_sessions = []
            for session_id, session in self.sessions.items():
                if session.is_expired():
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                self.cleanup_session(session_id)
                print(f"🧹 Cleaned up expired session: {session_id}")

    async def run_with_cancellation(
        self,
        session_id: str,
        coroutine,
        **kwargs
    ) -> AsyncGenerator[Any, None]:
        """
        Run a coroutine with session-based cancellation support

        Usage:
            async for result in manager.run_with_cancellation(session_id, streaming_function):
                yield result
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        task = asyncio.create_task(coroutine(**kwargs))
        session.add_task(task.get_name(), task)

        try:
            if asyncio.iscoroutine(coroutine):
                # Handle single coroutine
                await task
                yield await task
            else:
                # Handle async generator
                async for item in task:
                    if session.is_cancelled:
                        break
                    yield item

        except asyncio.CancelledError:
            print(f"🛑 Task cancelled for session {session_id}")
            raise
        finally:
            session.remove_task(task.get_name())


# Global streaming manager instance
streaming_manager = StreamingManager()


# Convenience functions for easy access
def create_streaming_session() -> str:
    """Create a new streaming session"""
    return streaming_manager.create_session()


def cancel_streaming_session(session_id: str) -> bool:
    """Cancel a streaming session"""
    return streaming_manager.cancel_session(session_id)

def clear_all_sessions() -> None:
    """Clear all streaming sessions"""
    streaming_manager.clear_all_sessions()

def is_session_cancelled(session_id: str) -> bool:
    """Check if session is cancelled"""
    return streaming_manager.is_session_cancelled(session_id)
