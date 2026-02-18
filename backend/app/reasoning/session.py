"""
Reasoning Session Management
Handles reasoning state, step tracking, and session persistence
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import uuid
from app.chat.service import save_reasoning_session, save_reasoning_step

logger = logging.getLogger(__name__)

# In-memory session storage (can be upgraded to Redis for distributed systems)
_reasoning_sessions: Dict[str, Dict[str, Any]] = {}
_session_objects: Dict[str, 'ReasoningSession'] = {}

class ReasoningSession:
    """Manages a single reasoning session"""
    
    def __init__(self, session_id: str, conversation_id: Optional[str] = None):
        self.session_id = session_id
        self.conversation_id = conversation_id
        self.created_at = datetime.now()
        self.steps: List[Dict[str, Any]] = []
        self.current_step = 0
        self.state = "active"  # active, paused, completed, cancelled
        self.metadata = {}
        self.callbacks: List[Callable] = []
    
    def register_callback(self, callback: Callable) -> None:
        """Register a callback for session events"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
    
    def emit_event(self, event_type: str, data: Any) -> None:
        """Emit an event to all registered callbacks"""
        for callback in self.callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in reasoning session callback: {str(e)}")

    def add_step(self, step_data: Dict[str, Any]) -> None:
        """Add a reasoning step"""
        step = {
            "index": len(self.steps),
            "timestamp": datetime.now().isoformat(),
            **step_data
        }
        self.steps.append(step)
        self.current_step = len(self.steps) - 1
        logger.info(f"Added step {self.current_step} to session {self.session_id}")
        
        # Persist to database
        save_reasoning_step(self.session_id, step)
        
        # Emit event for new step
        self.emit_event("reasoning_step", step)
    
    def get_steps(self) -> List[Dict[str, Any]]:
        """Get all reasoning steps"""
        return self.steps
    
    def get_current_step(self) -> Optional[Dict[str, Any]]:
        """Get current reasoning step"""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None
    
    def branch_from_step(self, step_index: int) -> str:
        """Create a branch from a specific step"""
        if step_index >= len(self.steps):
            raise ValueError(f"Step {step_index} does not exist")
        
        # Create new session branched from this step
        branch_id = f"{self.session_id}_branch_{uuid.uuid4().hex[:8]}"
        branch_session = ReasoningSession(branch_id)
        
        # Copy steps up to branch point
        branch_session.steps = self.steps[:step_index + 1].copy()
        branch_session.current_step = step_index
        branch_session.metadata["parent_session"] = self.session_id
        branch_session.metadata["branch_point"] = step_index
        
        _reasoning_sessions[branch_id] = branch_session.__dict__
        logger.info(f"Created branch {branch_id} from session {self.session_id} at step {step_index}")
        
        return branch_id
    
    def pause(self) -> None:
        """Pause reasoning session"""
        self.state = "paused"
        logger.info(f"Paused session {self.session_id}")
    
    def resume(self) -> None:
        """Resume reasoning session"""
        self.state = "active"
        logger.info(f"Resumed session {self.session_id}")
    
    def complete(self) -> None:
        """Mark session as completed"""
        self.state = "completed"
        logger.info(f"Completed session {self.session_id}")
    
    def cancel(self) -> None:
        """Cancel reasoning session"""
        self.state = "cancelled"
        logger.info(f"Cancelled session {self.session_id}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "steps": self.steps,
            "current_step": self.current_step,
            "state": self.state,
            "metadata": self.metadata,
            "total_steps": len(self.steps)
        }


def start_reasoning_session(
    session_id: str, 
    conversation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Start a new reasoning session
    
    Args:
        session_id: Unique session identifier
        conversation_id: Optional conversation identifier
        metadata: Optional metadata for the session
        
    Returns:
        Session information
    """
    try:
        if session_id in _reasoning_sessions:
            logger.warning(f"Session {session_id} already exists")
            return _reasoning_sessions[session_id]
        
        session = ReasoningSession(session_id, conversation_id)
        if metadata:
            session.metadata.update(metadata)
        
        _reasoning_sessions[session_id] = session.to_dict()
        _session_objects[session_id] = session
        
        # Persist to database
        if conversation_id:
            save_reasoning_session(session_id, conversation_id, metadata)
            
        logger.info(f"Started reasoning session {session_id}")
        return _reasoning_sessions[session_id]
    
    except Exception as e:
        logger.error(f"Failed to start reasoning session: {str(e)}")
        raise


def finish_reasoning_session(session_id: str) -> Dict[str, Any]:
    """
    Finish a reasoning session and return summary
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session summary
    """
    try:
        if session_id not in _reasoning_sessions:
            logger.warning(f"Session {session_id} not found")
            return {"error": "Session not found"}
        
        session_data = _reasoning_sessions[session_id]
        session_data["state"] = "completed"
        session_data["completed_at"] = datetime.now().isoformat()
        
        summary = {
            "session_id": session_id,
            "total_steps": len(session_data.get("steps", [])),
            "state": "completed",
            "steps": session_data.get("steps", []),
            "metadata": session_data.get("metadata", {})
        }
        
        logger.info(f"Finished reasoning session {session_id} with {summary['total_steps']} steps")
        return summary
    
    except Exception as e:
        logger.error(f"Failed to finish reasoning session: {str(e)}")
        raise


def add_reasoning_step(session_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a step to an active reasoning session
    
    Args:
        session_id: Session identifier
        step_data: Step information
        
    Returns:
        Updated session data
    """
    try:
        if session_id not in _reasoning_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session_data = _reasoning_sessions[session_id]
        
        step = {
            "index": len(session_data.get("steps", [])),
            "timestamp": datetime.now().isoformat(),
            **step_data
        }
        
        if "steps" not in session_data:
            session_data["steps"] = []
        
        session_data["steps"].append(step)
        session_data["current_step"] = len(session_data["steps"]) - 1
        
        logger.info(f"Added step {step['index']} to session {session_id}")
        return session_data
    
    except Exception as e:
        logger.error(f"Failed to add reasoning step: {str(e)}")
        raise


def get_reasoning_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get reasoning session data
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session data or None if not found
    """
    return _reasoning_sessions.get(session_id)


def get_reasoning_session_object(session_id: str) -> Optional[ReasoningSession]:
    """
    Get the actual ReasoningSession object
    """
    return _session_objects.get(session_id)


def branch_reasoning_session(session_id: str, step_index: int) -> str:
    """
    Create a branch from a specific reasoning step
    
    Args:
        session_id: Parent session identifier
        step_index: Step to branch from
        
    Returns:
        New branch session ID
    """
    try:
        if session_id not in _reasoning_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session_data = _reasoning_sessions[session_id]
        steps = session_data.get("steps", [])
        
        if step_index >= len(steps):
            raise ValueError(f"Step {step_index} does not exist")
        
        # Create new branch session
        branch_id = f"{session_id}_branch_{uuid.uuid4().hex[:8]}"
        branch_data = {
            "session_id": branch_id,
            "created_at": datetime.now().isoformat(),
            "steps": steps[:step_index + 1].copy(),
            "current_step": step_index,
            "state": "active",
            "metadata": {
                "parent_session": session_id,
                "branch_point": step_index,
                **session_data.get("metadata", {})
            }
        }
        
        _reasoning_sessions[branch_id] = branch_data
        logger.info(f"Created branch {branch_id} from session {session_id} at step {step_index}")
        
        return branch_id
    
    except Exception as e:
        logger.error(f"Failed to branch reasoning session: {str(e)}")
        raise


def cancel_reasoning_session(session_id: str) -> Dict[str, Any]:
    """
    Cancel a reasoning session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Updated session data
    """
    try:
        if session_id not in _reasoning_sessions:
            logger.warning(f"Session {session_id} not found")
            return {"error": "Session not found"}
        
        session_data = _reasoning_sessions[session_id]
        session_data["state"] = "cancelled"
        session_data["cancelled_at"] = datetime.now().isoformat()
        
        logger.info(f"Cancelled reasoning session {session_id}")
        return session_data
    
    except Exception as e:
        logger.error(f"Failed to cancel reasoning session: {str(e)}")
        raise


def cleanup_expired_sessions(max_age_hours: int = 24) -> int:
    """
    Clean up expired reasoning sessions
    
    Args:
        max_age_hours: Maximum age in hours
        
    Returns:
        Number of sessions cleaned up
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_sessions = []
        
        for session_id, session_data in _reasoning_sessions.items():
            created_at = datetime.fromisoformat(session_data.get("created_at", ""))
            if created_at < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del _reasoning_sessions[session_id]
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired reasoning sessions")
        return len(expired_sessions)
    
    except Exception as e:
        logger.error(f"Failed to cleanup expired sessions: {str(e)}")
        return 0


def get_all_sessions() -> Dict[str, Dict[str, Any]]:
    """Get all active reasoning sessions"""
    return _reasoning_sessions.copy()
