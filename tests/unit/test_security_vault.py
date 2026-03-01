"""Testes unitários — CredentialVault."""

import pytest
from pathlib import Path

from neopilot.security.vault import CredentialVault


@pytest.fixture
def vault(tmp_path):
    return CredentialVault(vault_dir=tmp_path / "vault", master_password="test_password_123")


def test_set_and_get(vault):
    vault.set("openai_key", "sk-test-12345678")
    result = vault.get("openai_key")
    assert result == "sk-test-12345678"


def test_get_nonexistent(vault):
    result = vault.get("nonexistent_key")
    assert result is None


def test_delete(vault):
    vault.set("temp_key", "temp_value")
    assert vault.exists("temp_key")
    vault.delete("temp_key")
    assert not vault.exists("temp_key")


def test_exists(vault):
    assert not vault.exists("mykey")
    vault.set("mykey", "myvalue")
    assert vault.exists("mykey")


def test_list_keys(vault):
    vault.set("key1", "val1")
    vault.set("key2", "val2")
    vault.set("key3", "val3")
    keys = vault.list_keys()
    assert "key1" in keys
    assert "key2" in keys
    assert "key3" in keys
    assert len(keys) == 3


def test_overwrite(vault):
    vault.set("api_key", "first_value")
    vault.set("api_key", "second_value")
    assert vault.get("api_key") == "second_value"


def test_encryption_at_rest(vault, tmp_path):
    """Verifica que o valor não está em plaintext no disco."""
    vault.set("secret", "muito_secreto_123")

    # Lê o arquivo raw
    enc_file = tmp_path / "vault" / "credentials.enc"
    assert enc_file.exists()
    raw = enc_file.read_bytes()

    assert b"muito_secreto_123" not in raw
    assert b"secret" not in raw


def test_separate_vaults_independent(tmp_path):
    """Dois vaults com senhas diferentes são independentes."""
    v1 = CredentialVault(vault_dir=tmp_path / "v1", master_password="senha1")
    v2 = CredentialVault(vault_dir=tmp_path / "v2", master_password="senha2")

    v1.set("key", "value_from_v1")
    v2.set("key", "value_from_v2")

    assert v1.get("key") == "value_from_v1"
    assert v2.get("key") == "value_from_v2"
