"""
Authentication Dependencies

This module provides FastAPI dependencies for authentication and authorization.
"""

from fastapi import HTTPException, Cookie
from .core import verify_token

def get_current_user(access_token: str = Cookie(None)):
    """Dependency to get current user from access token cookie
    Returns consistent dictionary format for provider-level workflow compatibility
    Uses consistent strict authentication pattern across all routes
    """
    if not access_token:
        raise HTTPException(
            status_code=401, 
            detail={
                "success": False,
                "error": "Authentication required",
                "message": "Please log in to access this resource"
            }
        )
    
    try:
        user_id = verify_token(access_token)
        # Return consistent dictionary format for provider-level workflow
        return {
            "id": user_id,
            "user_id": user_id,
            "authenticated": True
        }
    except:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": "Invalid access token",
                "message": "Please log in again"
            }
        )
