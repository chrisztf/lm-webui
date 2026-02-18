# Route Categorization

## Public Routes (No Authentication Required)

### Authentication Routes
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration  
- `GET /api/auth/status` - Check if any user exists
- `POST /api/auth/refresh` - Token refresh (uses refresh token cookie)

## Protected Routes (Authentication Required)

### User Management
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - User logout

### Chat Routes
- `POST /api/chat` - Unified chat endpoint
- `GET /api/chat/conversations` - Get user conversations
- `GET /api/chat/conversations/{conversation_id}/messages` - Get conversation messages
- `DELETE /api/chat/conversations/{conversation_id}` - Delete conversation

### API Key Management
- `GET /api/api_keys` - List all API keys
- `GET /api/api_keys/{provider}` - Get specific API key
- `POST /api/api_keys` - Add API key
- `DELETE /api/api_keys/{provider}` - Delete API key

### Model Management
- `GET /api/models/local` - Get local GGUF models
- `GET /api/models/api` - Get API models
- `GET /api/models/api/all` - Get all API models
- `GET /api/models/api/dynamic` - Get dynamic models
- `POST /api/models/api/refresh` - Refresh models cache

### File Management
- `GET /api/download/{filename}` - Download files
- `GET /api/history/conversation/{conversation_id}/files` - Get file references

### Settings
- `GET /api/settings` - Get user settings
- `POST /api/settings` - Update user settings

### Image Generation
- `GET /api/images/models` - Get image models
- `POST /api/images/generate/{provider}` - Generate images

### History & Sessions
- `GET /api/history/conversations` - List conversations
- `POST /api/history/conversation/{conversation_id}/title` - Update conversation title
- `DELETE /api/history/conversation/{conversation_id}` - Delete conversation
- `GET /api/sessions` - Get user sessions
- `GET /api/sessions/current` - Get current session
- `POST /api/sessions` - Create session
- `DELETE /api/sessions/{session_id}` - Delete session

### Intent Verification
- `POST /api/intents/verify` - Verify user intent

## Implementation Standards

### Backend Dependencies
All protected routes MUST use the standardized dependency:
```python
from app.security.auth.dependencies import get_current_user

@router.get("/protected-endpoint")
async def protected_endpoint(user: dict = Depends(get_current_user)):
    # Use user["id"] for database queries
    user_id = user["id"]
```

### Frontend Authentication
All protected API calls MUST use:
- `authFetch()` for regular requests
- `authenticatedStreamingFetch()` for streaming requests
- `credentials: 'include'` for cookie-based authentication

### Error Handling
All authentication errors MUST return consistent 401 responses:
```json
{
  "success": false,
  "error": "Authentication required",
  "message": "Please log in to access this resource"
}
```

### Route Protection Enforcement
- All new routes must be categorized as public or protected
- Protected routes must use `get_current_user` dependency
- Public routes must not require authentication
- Route categorization must be documented here
