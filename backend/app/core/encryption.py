"""Encryption utilities for API keys.

NOTE: Currently a passthrough. Replace with real encryption (e.g. Fernet,
Azure Key Vault, HashiCorp Vault) before storing keys in production.
"""


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key.

    Args:
        encrypted_key: The encrypted or plaintext API key.

    Returns:
        The decrypted API key string.
    """
    # TODO: implement actual decryption if/when keys are encrypted at rest.
    return encrypted_key or ""
