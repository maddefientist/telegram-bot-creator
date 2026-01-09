"""Security utilities - encryption, CSRF, etc."""
import hashlib
import hmac
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode

from cryptography.fernet import Fernet, InvalidToken

from config import get_settings

settings = get_settings()


def get_fernet() -> Fernet:
    """Get Fernet instance for encryption."""
    return Fernet(settings.encryption_key.encode())


def encrypt_token(token: str) -> str:
    """Encrypt a sensitive token (e.g., Telegram bot token)."""
    f = get_fernet()
    encrypted = f.encrypt(token.encode())
    return encrypted.decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a sensitive token."""
    f = get_fernet()
    try:
        decrypted = f.decrypt(encrypted_token.encode())
        return decrypted.decode()
    except InvalidToken:
        raise ValueError("Invalid or corrupted encrypted token")


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, stored_token: str) -> bool:
    """Verify a CSRF token using constant-time comparison."""
    return hmac.compare_digest(token, stored_token)


def generate_reference_key() -> str:
    """Generate a unique reference key for Solana Pay invoices.

    Returns a base58-encoded 32-byte public key style reference.
    """
    # Generate 32 random bytes (like a Solana public key)
    random_bytes = secrets.token_bytes(32)

    # Base58 encode (Solana style)
    import base58
    return base58.b58encode(random_bytes).decode()


def generate_webhook_signature(payload: bytes, secret: str) -> str:
    """Generate HMAC signature for webhook payloads."""
    signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify a webhook signature."""
    expected = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected)


def mask_token(token: str, visible_chars: int = 8) -> str:
    """Mask a token for display, showing only first/last chars."""
    if len(token) <= visible_chars * 2:
        return "*" * len(token)

    return f"{token[:visible_chars]}...{token[-visible_chars:]}"


def sanitize_log_data(data: dict) -> dict:
    """Remove sensitive fields from data before logging."""
    sensitive_fields = {
        "password",
        "token",
        "secret",
        "api_key",
        "telegram_token",
        "encryption_key",
        "jwt_secret",
        "csrf_secret",
    }

    sanitized = {}
    for key, value in data.items():
        if any(s in key.lower() for s in sensitive_fields):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value

    return sanitized
