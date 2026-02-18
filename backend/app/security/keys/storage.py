import sqlite3
from typing import Optional
from cryptography.fernet import Fernet

from database import get_db
from ..encryption import encrypt_value, decrypt_value

def store_api_key(user_id: int, provider: str, api_key: str) -> None:
    """Store an encrypted API key for a user"""
    encrypted_key = encrypt_value(api_key)
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Check if API key already exists for this user and provider
        cursor.execute(
            "SELECT id FROM api_keys WHERE user_id = ? AND provider = ?",
            (user_id, provider)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing API key
            cursor.execute(
                "UPDATE api_keys SET api_key = ? WHERE user_id = ? AND provider = ?",
                (encrypted_key, user_id, provider)
            )
        else:
            # Insert new API key
            cursor.execute(
                "INSERT INTO api_keys (user_id, provider, api_key) VALUES (?, ?, ?)",
                (user_id, provider, encrypted_key)
            )
        
        conn.commit()
    finally:
        conn.close()

def get_api_key(user_id: int, provider: str) -> Optional[str]:
    """Get and decrypt an API key for a user"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT api_key FROM api_keys WHERE user_id = ? AND provider = ?",
            (user_id, provider)
        )
        result = cursor.fetchone()
        
        if result:
            return decrypt_value(result[0])
        return None
    finally:
        conn.close()

def delete_api_key(user_id: int, provider: str) -> bool:
    """Delete an API key for a user"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "DELETE FROM api_keys WHERE user_id = ? AND provider = ?",
            (user_id, provider)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def list_api_keys(user_id: int) -> list:
    """List all API keys for a user (without decrypting the keys)"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT provider, created_at FROM api_keys WHERE user_id = ?",
            (user_id,)
        )
        results = cursor.fetchall()
        
        return [
            {"provider": row[0], "created_at": row[1]}
            for row in results
        ]
    finally:
        conn.close()

def reencrypt_all_api_keys(old_fernet: Fernet, new_fernet: Fernet) -> int:
    """Re-encrypt all API keys with a new Fernet key (for key rotation)"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get all API keys
        cursor.execute("SELECT id, api_key FROM api_keys")
        api_keys = cursor.fetchall()
        
        reencrypted_count = 0
        
        for api_key_id, encrypted_key in api_keys:
            try:
                # Decrypt with old key
                decrypted_key = old_fernet.decrypt(encrypted_key.encode())
                # Re-encrypt with new key
                new_encrypted_key = new_fernet.encrypt(decrypted_key).decode()
                
                # Update in database
                cursor.execute(
                    "UPDATE api_keys SET api_key = ? WHERE id = ?",
                    (new_encrypted_key, api_key_id)
                )
                reencrypted_count += 1
            except Exception:
                # If decryption fails, skip this key (it might be corrupted or encrypted with different key)
                continue
        
        conn.commit()
        return reencrypted_count
    finally:
        conn.close()
