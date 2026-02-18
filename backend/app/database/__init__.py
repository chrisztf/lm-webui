"""
Unified Database Interface
Provides backward compatibility for old imports while using new hybrid architecture
"""

from .sqlite.connection_pool import get_db, database_manager
from .sqlite.files import SQLiteFileManager
from .migration import init_db, reset_db, db_info

__all__ = ["get_db", "init_db", "SQLiteFileManager", "database_manager", "reset_db", "db_info"]
