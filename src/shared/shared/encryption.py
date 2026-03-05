"""Fernet encryption for sensitive data at rest (OAuth tokens, etc.)."""
from cryptography.fernet import Fernet
from .settings_service import get_setting

_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = get_setting('ENCRYPTION_KEY')
        if not key:
            raise RuntimeError("ENCRYPTION_KEY not configured. Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
        _fernet = Fernet(key.encode())
    return _fernet


def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
