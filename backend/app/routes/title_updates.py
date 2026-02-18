"""
SSE (Server-Sent Events) endpoint for real-time title updates
Provides push-based title updates for conversations
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.security.auth.dependencies import get_current_user
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/conversations")

# Active SSE connections tracking
_active_connections: Dict[str, Set[asyncio.Queue]] = {}

async def _check_title_update(conversation_id: str, user_id: int) -> Optional[str]:
    """Check if conversation title has been updated"""
    db = get_db()
    
    # Get current title from database
    result = db.execute(
        "SELECT title FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id)
    ).fetchone()
    
    if not result:
        return None
    
    current_title = result[0]
    if current_title and current_title != "New Chat":
        return current_title
    
    return None

async def _wait_for_title_update(conversation_id: str, user_id: int, timeout_seconds: int = 30) -> Optional[str]:
    """Wait for title update with timeout"""
    start_time = datetime.now()
    
    while (datetime.now() - start_time).seconds < timeout_seconds:
        title = await _check_title_update(conversation_id, user_id)
        if title:
            return title
        
        # Wait 1 second before checking again
        await asyncio.sleep(1)
    
    return None

@router.get("/{conversation_id}/title-updates")
async def stream_title_updates(
    conversation_id: str,
    user_id: dict = Depends(get_current_user)
):
    """
    SSE endpoint for real-time title updates
    Streams title updates when they become available
    """
    user_id_int = user_id["id"]
    
    # Verify conversation exists and belongs to user
    db = get_db()
    conversation = db.execute(
        "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id_int)
    ).fetchone()
    
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    
    async def event_generator():
        """Generate SSE events for title updates"""
        try:
            # Register this connection
            if conversation_id not in _active_connections:
                _active_connections[conversation_id] = set()
            
            event_queue = asyncio.Queue()
            _active_connections[conversation_id].add(event_queue)
            
            logger.info(f"SSE connection started for conversation {conversation_id}, user {user_id_int}")
            
            try:
                # Check for existing title first
                current_title = await _check_title_update(conversation_id, user_id_int)
                if current_title and current_title != "New Chat":
                    logger.info(f"Found existing title for {conversation_id}: {current_title}")
                    yield f"data: {json.dumps({'title': current_title, 'type': 'title_update'})}\n\n"
                    return
                
                # Wait for title update (max 30 seconds)
                logger.info(f"Waiting for title update for {conversation_id}")
                updated_title = await _wait_for_title_update(conversation_id, user_id_int, timeout_seconds=30)
                
                if updated_title:
                    logger.info(f"Title updated for {conversation_id}: {updated_title}")
                    yield f"data: {json.dumps({'title': updated_title, 'type': 'title_update'})}\n\n"
                else:
                    logger.info(f"No title update for {conversation_id} within timeout")
                    yield f"data: {json.dumps({'type': 'timeout', 'message': 'No title update received'})}\n\n"
                    
            finally:
                # Cleanup connection
                if conversation_id in _active_connections:
                    _active_connections[conversation_id].discard(event_queue)
                    if not _active_connections[conversation_id]:
                        del _active_connections[conversation_id]
                
                logger.info(f"SSE connection closed for conversation {conversation_id}")
                
        except asyncio.CancelledError:
            logger.info(f"SSE connection cancelled for conversation {conversation_id}")
            raise
        except Exception as e:
            logger.error(f"SSE error for conversation {conversation_id}: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

async def broadcast_title_update(conversation_id: str, title: str):
    """Broadcast title update to all active SSE connections for this conversation"""
    if conversation_id not in _active_connections:
        return
    
    message = json.dumps({"title": title, "type": "title_update", "timestamp": datetime.now().isoformat()})
    event_data = f"data: {message}\n\n"
    
    # Send to all active connections
    for queue in list(_active_connections[conversation_id]):
        try:
            await queue.put(event_data)
        except Exception as e:
            logger.error(f"Failed to send title update to queue: {str(e)}")
    
    logger.info(f"Broadcast title update for {conversation_id}: {title} to {len(_active_connections[conversation_id])} connections")

def cleanup_inactive_connections(max_age_minutes: int = 60):
    """Clean up inactive connections (call periodically)"""
    # This is a simple implementation - in production, you'd want to track
    # connection age and remove stale connections
    pass

# WebSocket fallback notification (optional integration)
async def notify_title_update_via_websocket(conversation_id: str, title: str, user_id: int):
    """Notify WebSocket connections about title update (for hybrid approach)"""
    try:
        from app.routes.websocket import broadcast_conversation_update
        await broadcast_conversation_update(user_id, conversation_id, title)
    except ImportError:
        logger.warning("WebSocket module not available for title notifications")
    except Exception as e:
        logger.error(f"WebSocket notification failed: {str(e)}")

# Health check endpoint
@router.get("/{conversation_id}/title-updates/health")
async def title_updates_health(conversation_id: str, user_id: dict = Depends(get_current_user)):
    """Health check for title updates SSE endpoint"""
    active_count = len(_active_connections.get(conversation_id, set()))
    
    return {
        "conversation_id": conversation_id,
        "active_connections": active_count,
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }
