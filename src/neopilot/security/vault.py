"""
NeoPilot Credential Vault
Armazenamento seguro de credenciais com AES-256-GCM + PBKDF2.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CredentialVault:
    """
    Cofre de credenciais com criptografia AES-256-GCM.
    A chave mestre é derivada da senha do usuário via PBKDF2-SHA256.
    """

    VAULT_FILE = Path("~/.neopilot/vault/credentials.enc")
    SALT_FILE = Path("~/.neopilot/vault/.salt")
    ITERATIONS = 600_000

    def __init__(self, master_password: str, vault_dir: Optional[Path] = None):
        if vault_dir:
            self.vault_path = vault_dir / "credentials.enc"
            self.salt_path = vault_dir / ".salt"
        else:
            self.vault_path = self.VAULT_FILE.expanduser()
            self.salt_path = self.SALT_FILE.expanduser()
        self.vault_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        self._key = self._derive_key(master_password)
        self._data: dict[str, str] = {}

        if self.vault_path.exists():
            self._load()

    def _get_or_create_salt(self) -> bytes:
        if self.salt_path.exists():
            return self.salt_path.read_bytes()
        salt = os.urandom(32)
        self.salt_path.write_bytes(salt)
        self.salt_path.chmod(0o600)
        return salt

    def _derive_key(self, password: str) -> bytes:
        salt = self._get_or_create_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.ITERATIONS,
        )
        return kdf.derive(password.encode("utf-8"))

    def _encrypt(self, plaintext: str) -> bytes:
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ct)

    def _decrypt(self, ciphertext: bytes) -> str:
        aesgcm = AESGCM(self._key)
        raw = base64.b64decode(ciphertext)
        nonce, ct = raw[:12], raw[12:]
        return aesgcm.decrypt(nonce, ct, None).decode("utf-8")

    def _load(self) -> None:
        encrypted = self.vault_path.read_bytes()
        plaintext = self._decrypt(encrypted)
        self._data = json.loads(plaintext)

    def _save(self) -> None:
        plaintext = json.dumps(self._data, ensure_ascii=False)
        encrypted = self._encrypt(plaintext)
        self.vault_path.write_bytes(encrypted)
        self.vault_path.chmod(0o600)

    def set(self, key: str, value: str) -> None:
        """Armazena credencial no vault."""
        self._data[key] = value
        self._save()

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Recupera credencial do vault."""
        return self._data.get(key, default)

    def delete(self, key: str) -> bool:
        """Remove credencial do vault."""
        if key in self._data:
            del self._data[key]
            self._save()
            return True
        return False

    def list_keys(self) -> list[str]:
        """Lista chaves armazenadas (sem valores)."""
        return list(self._data.keys())

    def exists(self, key: str) -> bool:
        return key in self._data
