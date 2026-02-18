from cryptography.fernet import Fernet
from pathlib import Path
import os
from typing import Optional

def get_fernet_key():
    """Get or generate Fernet key from .secrets directory"""
    key_file = Path(".secrets/fernet_secret")
    key_file.parent.mkdir(exist_ok=True)
    if key_file.exists():
        return key_file.read_bytes()
    key = Fernet.generate_key()
    key_file.write_bytes(key)
    key_file.chmod(0o600)
    return key

def get_fernet_from_env():
    """Get Fernet key from environment variable"""
    secret_key = os.environ.get("FERNET_SECRET_KEY")
    if not secret_key:
        # generate once and save for deployment
        secret_key = Fernet.generate_key().decode()
        print("Generated Fernet key, set as FERNET_SECRET_KEY env var:", secret_key)
    return Fernet(secret_key.encode())

# Main cipher instance using file-based key storage
cipher = Fernet(get_fernet_key())

def encrypt_value(value: str) -> str:
    """Encrypt a string value using Fernet (main encryption function)"""
    return cipher.encrypt(value.encode()).decode()

def decrypt_value(value: str) -> str:
    """Decrypt a Fernet-encrypted string value (main decryption function)"""
    return cipher.decrypt(value.encode()).decode()

def encrypt_key(plaintext: str) -> str:
    """Alias for encrypt_value - maintained for backward compatibility"""
    return encrypt_value(plaintext)

def decrypt_key(encrypted: str) -> str:
    """Alias for decrypt_value - maintained for backward compatibility"""
    return decrypt_value(encrypted)
