"""
Unified Context Middleware
Automatically attaches user, conversation, and message context to every request
"""

from fastapi import Request, Response
from typing import Optional, Dict, Any
import jwt
from app.security.auth.core import get_secret_key

class RequestContext:
    """Unified request context container"""
    
    def __init__(self, user_id: Optional[int] = None, 
                 conversation_id: Optional[str] = None,
                 message_id: Optional[str] = None):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.message_id = message_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id
        }
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.user_id is not None

class ContextMiddleware:
    """Middleware class for unified context"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Extract and attach context
        context = await self.extract_context(request)
        request.state.context = context
        
        # Create response wrapper
        response = await self.app(scope, receive, send)
        return response
    
    async def extract_context(self, request: Request) -> RequestContext:
        """Extract context from request headers and JWT"""
        context = RequestContext()
        
        # Extract from headers
        conversation_id = request.headers.get("X-Conversation-ID")
        message_id = request.headers.get("X-Message-ID")

        if conversation_id:
            context.conversation_id = conversation_id
        if message_id:
            context.message_id = message_id

        # Extract user from JWT (if available)
        auth_header = request.headers.get("Authorization")
        print(f"🔍 Auth header present: {bool(auth_header and auth_header.startswith('Bearer '))}")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Use the same secret key as auth core (already base64 encoded)
                jwt_secret_str = get_secret_key()
                # Decode JWT to get user info
                payload = jwt.decode(
                    token,
                    jwt_secret_str,
                    algorithms=["HS256"]
                )
                context.user_id = int(payload.get("sub"))
                print(f"✅ JWT decoded successfully, user_id: {context.user_id}")
            except jwt.InvalidTokenError as e:
                # Token is invalid, continue without user context
                print(f"❌ JWT decode failed: {str(e)}")
                pass
        else:
            print("❌ No Bearer token in Authorization header")

        return context

async def attach_context_middleware(request: Request, call_next):
    """
    Function-based middleware for unified context
    
    This can be used as an alternative to the class-based middleware
    """
    # Extract context
    context = await extract_context_from_request(request)
    request.state.context = context
    
    # Log request with context
    log_request_with_context(request, context)
    
    # Process request
    response = await call_next(request)
    
    return response

async def extract_context_from_request(request: Request) -> RequestContext:
    """Extract context from request (shared function)"""
    context = RequestContext()
    
    # Extract from headers
    conversation_id = request.headers.get("X-Conversation-ID")
    message_id = request.headers.get("X-Message-ID")
    
    if conversation_id:
        context.conversation_id = conversation_id
    if message_id:
        context.message_id = message_id
    
    # Extract user from JWT (if available) - check both Authorization header and cookies
    token = None
    
    # Check Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    
    # If no token in header, check cookies
    if not token:
        token = request.cookies.get("access_token")
    
    if token:
        try:
            # Use the same secret key as auth core (already base64 encoded)
            jwt_secret_str = get_secret_key()
            # Decode JWT to get user info
            payload = jwt.decode(
                token,
                jwt_secret_str,
                algorithms=["HS256"]
            )
            context.user_id = int(payload.get("sub"))
        except jwt.InvalidTokenError:
            # Token is invalid, continue without user context
            pass
    
    return context

def log_request_with_context(request: Request, context: RequestContext):
    """Log request with context information"""
    method = request.method
    path = request.url.path
    user_info = f"user:{context.user_id}" if context.user_id else "anonymous"
    conv_info = f"conv:{context.conversation_id}" if context.conversation_id else "no-conv"
    
    print(f"🌐 {method} {path} [{user_info}] [{conv_info}]")

# Convenience function to get context from request
def get_request_context(request: Request) -> RequestContext:
    """Get context from request state"""
    return getattr(request.state, "context", RequestContext())
