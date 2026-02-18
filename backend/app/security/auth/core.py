"""
Core Authentication Functions

This module provides the core authentication functionality including:
- JWT token creation and verification
- Password hashing and verification
- Secret key management
"""

from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from pathlib import Path
import secrets

# Persistent secret key management
def get_secret_key():
    """Get or create persistent JWT secret key from .secrets directory (migrated from legacy secrets/)"""
    secret_file = Path(".secrets/jwt_secret")
    secret_file.parent.mkdir(exist_ok=True)
    if secret_file.exists():
        # Read binary secret and convert to base64 string for JWT
        import base64
        secret_bytes = secret_file.read_bytes()
        return base64.urlsafe_b64encode(secret_bytes).decode()
    # Generate new secret as bytes and save
    secret_bytes = secrets.token_bytes(32)  # 32 bytes = 256 bits
    secret_file.write_bytes(secret_bytes)
    secret_file.chmod(0o600)
    # Return as base64 string
    import base64
    return base64.urlsafe_b64encode(secret_bytes).decode()

# Configuration
SECRET_KEY = get_secret_key()
ALGORITHM = "HS256"

# Password context - using pbkdf2_sha256 for better security
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Token functions
def create_access_token(user_id: int) -> str:
    """Create 60-minute access token"""
    expire = datetime.utcnow() + timedelta(minutes=60)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, ALGORITHM)

def create_refresh_token(user_id: int) -> str:
    """Create 7-day refresh token"""
    expire = datetime.utcnow() + timedelta(days=7)
    return jwt.encode({"sub": str(user_id), "exp": expire, "type": "refresh"}, SECRET_KEY, ALGORITHM)

def verify_token(token: str) -> int:
    """Verify token and return user_id"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return int(payload["sub"])

# Password functions
def hash_password(password: str) -> str:
    """Hash a password using the configured context"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)
