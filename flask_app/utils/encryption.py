"""
encryption.py
─────────────
Transparent field-level encryption for sensitive database columns.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` package.
The ENCRYPTION_KEY environment variable must be a 32-byte URL-safe base64
value, generated once with:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

If ENCRYPTION_KEY is not set the TypeDecorator falls back to plaintext,
so the app still runs in environments that haven't set the key (e.g. tests).
A warning is printed on startup if the key is missing.

Usage
─────
    from flask_app.utils.encryption import EncryptedText

    class SchwabToken(db.Model):
        access_token  = db.Column(EncryptedText, nullable=False)
        refresh_token = db.Column(EncryptedText, nullable=False)
"""

import os
import warnings
from sqlalchemy import TypeDecorator, Text
from cryptography.fernet import Fernet, InvalidToken


def _get_fernet() -> Fernet | None:
    """Return a Fernet instance using ENCRYPTION_KEY, or None if not set."""
    raw_key = os.getenv('ENCRYPTION_KEY', '').strip()
    if not raw_key:
        return None
    try:
        return Fernet(raw_key.encode())
    except Exception:
        warnings.warn(
            "ENCRYPTION_KEY is set but invalid — field encryption disabled.",
            RuntimeWarning, stacklevel=2,
        )
        return None


class EncryptedText(TypeDecorator):
    """
    SQLAlchemy TypeDecorator that transparently encrypts on write
    and decrypts on read using Fernet symmetric encryption.

    Falls back gracefully to plaintext when ENCRYPTION_KEY is missing,
    and tolerates existing plaintext rows when decryption fails (so a
    key can be added to a database that previously had none).
    """
    impl    = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt before writing to the database."""
        if value is None:
            return None
        fernet = _get_fernet()
        if fernet is None:
            return value
        return fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        """Decrypt after reading from the database."""
        if value is None:
            return None
        fernet = _get_fernet()
        if fernet is None:
            return value
        try:
            return fernet.decrypt(value.encode()).decode()
        except (InvalidToken, Exception):
            # Row was written before encryption was enabled — return as-is.
            # After all rows are re-encrypted this branch will never fire.
            return value
