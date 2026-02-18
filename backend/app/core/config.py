"""
Configuration module for backward compatibility.

This module provides backward compatibility for existing code that imports
from `app.core.config`. New code should use `app.core.config_manager` instead.
"""

import os
import secrets
import base64
from pathlib import Path
from typing import Optional

# Import the new configuration manager
from .config_manager import (
    config_manager,
    get_config,
    get_database_config,
    get_security_config,
    get_paths_config,
    get_llm_config,
    get_server_config,
    get_media_dir,
    get_data_dir,
    get_database_path as new_get_database_path,
    is_development,
    is_production,
    is_testing
)

# Configuration for secrets management (kept for backward compatibility)
# Note: Secrets are stored in .secrets directory (relative to backend root)
SECRETS_DIR = Path(".secrets")
JWT_SECRET_FILE = SECRETS_DIR / "jwt_secret"
FERNET_SECRET_FILE = SECRETS_DIR / "fernet_secret"

def load_or_create_secret(file_path: Path, length: int = 32) -> bytes:
    """Load existing secret or generate and save a new one"""
    SECRETS_DIR.mkdir(exist_ok=True)
    
    if file_path.exists():
        return file_path.read_bytes()
    
    # Generate new secret
    new_secret = secrets.token_bytes(length)
    file_path.write_bytes(new_secret)
    return new_secret

def load_or_create_fernet_secret(file_path: Path) -> bytes:
    """Load existing Fernet secret or generate and save a new one"""
    SECRETS_DIR.mkdir(exist_ok=True)
    
    if file_path.exists():
        return file_path.read_bytes()
    
    # Generate new Fernet key (must be 32 url-safe base64-encoded bytes)
    new_secret = base64.urlsafe_b64encode(secrets.token_bytes(32))
    file_path.write_bytes(new_secret)
    return new_secret

# Load or create secrets (backward compatibility)
JWT_SECRET = load_or_create_secret(JWT_SECRET_FILE)
FERNET_SECRET = load_or_create_fernet_secret(FERNET_SECRET_FILE)

# Database configuration (backward compatibility)
DATABASE_URL = get_database_config().url

def get_database_path() -> str:
    """
    Get the absolute path to the SQLite database file.
    Ensures consistent path resolution across the application.
    
    Note: This function is kept for backward compatibility.
    New code should use `get_database_path()` from config_manager.
    """
    return new_get_database_path()

# JWT configuration (backward compatibility)
ACCESS_TOKEN_EXPIRE_MINUTES = get_security_config().access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = 30  # Default value, not in new config

# API configuration (backward compatibility)
API_V1_PREFIX = "/api"

# Environment variables for backward compatibility
def get_env_var(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable with backward compatibility.
    
    Note: New code should use the configuration manager instead.
    """
    return os.getenv(name, default)

# Legacy functions for backward compatibility
def get_base_dir() -> Path:
    """Get base directory (backward compatibility)"""
    return Path(get_paths_config().base_dir).resolve()

def get_media_dir_path() -> Path:
    """Get media directory path (backward compatibility)"""
    return get_media_dir()

def get_data_dir_path() -> Path:
    """Get data directory path (backward compatibility)"""
    return get_data_dir()

# Deprecation warnings
import warnings
import inspect

def _warn_deprecated():
    """Warn about deprecated usage"""
    caller = inspect.stack()[2]
    warnings.warn(
        f"Import from app.core.config is deprecated. "
        f"Use app.core.config_manager instead. "
        f"Called from {caller.filename}:{caller.lineno}",
        DeprecationWarning,
        stacklevel=3
    )

# Warn on import of deprecated constants
_warn_deprecated()
