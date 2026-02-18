# Authentication System for AIMO-WebUI

A lightweight, secure authentication layer for the AIMO-WebUI backend using FastAPI, SQLite, bcrypt, and JWT tokens.

## Features

- **Secure Password Hashing**: Uses bcrypt with salt for password storage
- **JWT-based Authentication**: Short-lived access tokens with long-lived refresh tokens
- **Auto-login (Remember Me)**: Persistent login sessions with refresh tokens
- **Device Binding**: Optional device ID tracking for enhanced security
- **Token Rotation**: Refresh tokens are rotated on each use
- **Rate Limiting**: Basic in-memory rate limiting for login attempts
- **SQLite Storage**: Lightweight, file-based database (easily replaceable)

## Environment Variables

Add these to your `.env` file:

```env
JWT_SECRET=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
```

## API Endpoints

### Authentication Endpoints

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get access token
- `POST /auth/refresh` - Refresh access token using refresh token
- `POST /auth/logout` - Logout and revoke refresh token
- `GET /auth/me` - Get current user information (protected)

### Request/Response Examples

#### Register
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "securepassword",
    "device_id": "optional-device-id"
  }'
```

#### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "securepassword",
    "remember_me": true,
    "device_id": "optional-device-id"
  }'
```

#### Refresh Token
```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Cookie: refresh_token=your-refresh-token"
```

#### Get Current User (Protected)
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer your-access-token"
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_id TEXT NULL
);
```

### Refresh Tokens Table
```sql
CREATE TABLE refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL,
    device_id TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    revoked INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## Security Features

### Password Security
- Uses bcrypt with automatic salt generation
- Default work factor of 12 (configurable)
- Protection against timing attacks

### Token Security
- **Access Tokens**: Short-lived (15 minutes by default)
- **Refresh Tokens**: Long-lived (30 days by default), stored server-side
- **HttpOnly Cookies**: Refresh tokens sent as secure cookies
- **Token Rotation**: Refresh tokens are rotated on each use
- **Revocation**: Tokens can be individually or globally revoked

### Rate Limiting
- 5 login attempts per 15 minutes per username
- Prevents brute force attacks
- Simple in-memory implementation (reset on server restart)

## Usage in Other Endpoints

To protect your API endpoints, use the `get_current_user` dependency:

```python
from app.auth.routes import get_current_user
from app.auth.models import UserResponse

@router.get("/protected-endpoint")
async def protected_endpoint(current_user: UserResponse = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}", "data": "protected_data"}
```

## Cookie Configuration

### Development (HTTP)
```python
response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=False,  # Set to False for development
    samesite="strict",
    path="/auth/refresh",
    max_age=max_age
)
```

### Production (HTTPS)
```python
response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=True,  # Set to True for production
    samesite="strict",
    path="/auth/refresh",
    max_age=max_age
)
```

## Fallback for Non-Browser Clients

For environments where cookies are not available (mobile apps, desktop apps), the refresh token can be passed in the request body:

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your-refresh-token"}'
```

## Testing

Run the authentication tests:

```bash
cd backend
python test_auth.py
```

## Migration to Production Database

The current implementation uses SQLite for simplicity. To migrate to a production database (PostgreSQL, MySQL, etc.):

1. Replace SQLite connection logic in `models.py`
2. Update SQL queries to match your database syntax
3. Consider connection pooling for better performance

## Security Best Practices

1. **Use HTTPS in production**: Always enable SSL/TLS
2. **Set strong JWT_SECRET**: Use a long, random secret key
3. **Monitor login attempts**: Implement logging for suspicious activity
4. **Regular token rotation**: Consider shorter token lifetimes for sensitive applications
5. **Device management**: Implement device revocation for lost/stolen devices

## File Structure

```
backend/app/auth/
├── __init__.py          # Module initialization
├── models.py            # Database schema and Pydantic models
├── crud.py              # Database operations
├── security.py          # Password hashing and JWT utilities
├── routes.py            # FastAPI endpoints
└── README.md            # This file
```

## Dependencies

- `passlib[bcrypt]` - Password hashing
- `pyjwt` - JWT token handling
- `python-dotenv` - Environment variable management
- `fastapi` - Web framework
- `uvicorn[standard]` - ASGI server
