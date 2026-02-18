"""
Reasoning Service Layer

Handles structured reasoning for deep thinking mode with clean separation from WebSocket.
Integrates with StreamingService for reasoning-enhanced responses.
"""
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import uuid
from app.chat.service import save_reasoning_session, save_reasoning_step

logger = logging.getLogger(__name__)


class ReasoningService:
    """Service for managing structured reasoning sessions"""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_objects: Dict[str, 'ReasoningSession'] = {}
    
    def start_session(
        self,
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
            if session_id in self._sessions:
                logger.warning(f"Session {session_id} already exists")
                return self._sessions[session_id]
            
            session = ReasoningSession(session_id, conversation_id)
            if metadata:
                session.metadata.update(metadata)
            
            self._sessions[session_id] = session.to_dict()
            self._session_objects[session_id] = session
            
            # Persist to database
            if conversation_id:
                save_reasoning_session(session_id, conversation_id, metadata)
                
            logger.info(f"Started reasoning session {session_id}")
            return self._sessions[session_id]
        
        except Exception as e:
            logger.error(f"Failed to start reasoning session: {str(e)}")
            raise
    
    def finish_session(self, session_id: str) -> Dict[str, Any]:
        """
        Finish a reasoning session and return summary
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary
        """
        try:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found")
                return {"error": "Session not found"}
            
            session_data = self._sessions[session_id]
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
    
    def add_step(self, session_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a step to an active reasoning session
        
        Args:
            session_id: Session identifier
            step_data: Step information
            
        Returns:
            Updated session data
        """
        try:
            if session_id not in self._sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session_data = self._sessions[session_id]
            
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
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get reasoning session data
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        return self._sessions.get(session_id)
    
    def get_session_object(self, session_id: str) -> Optional['ReasoningSession']:
        """
        Get the actual ReasoningSession object
        """
        return self._session_objects.get(session_id)
    
    def branch_session(self, session_id: str, step_index: int) -> str:
        """
        Create a branch from a specific reasoning step
        
        Args:
            session_id: Parent session identifier
            step_index: Step to branch from
            
        Returns:
            New branch session ID
        """
        try:
            if session_id not in self._sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session_data = self._sessions[session_id]
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
            
            self._sessions[branch_id] = branch_data
            logger.info(f"Created branch {branch_id} from session {session_id} at step {step_index}")
            
            return branch_id
        
        except Exception as e:
            logger.error(f"Failed to branch reasoning session: {str(e)}")
            raise
    
    def cancel_session(self, session_id: str) -> Dict[str, Any]:
        """
        Cancel a reasoning session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Updated session data
        """
        try:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found")
                return {"error": "Session not found"}
            
            session_data = self._sessions[session_id]
            session_data["state"] = "cancelled"
            session_data["cancelled_at"] = datetime.now().isoformat()
            
            logger.info(f"Cancelled reasoning session {session_id}")
            return session_data
        
        except Exception as e:
            logger.error(f"Failed to cancel reasoning session: {str(e)}")
            raise


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


# Global reasoning service instance
_reasoning_service = None

def get_reasoning_service() -> ReasoningService:
    """Get global reasoning service instance"""
    global _reasoning_service
    if _reasoning_service is None:
        _reasoning_service = ReasoningService()
    return _reasoning_service
