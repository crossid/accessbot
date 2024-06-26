from unittest.mock import patch

import pytest

from app.vault_env_vars import EnvVarVault


@pytest.fixture
def vault_env():
    vault = EnvVarVault()
    workspace_id = "acme"
    path = "test_path"
    secret = "secret_value"
    return vault, workspace_id, path, secret


@patch.dict("os.environ", {}, clear=True)
def test_set_get_list_secret(vault_env):
    vault, workspace_id, path, secret = vault_env
    # Test set_secret
    result = vault.set_secret(workspace_id, path, secret)
    assert result, "Set secret should return True"

    # Test get_secret
    retrieved_secret = vault.get_secret(workspace_id, path)
    assert retrieved_secret == secret, "Retrieved secret should match the set value"

    vault.set_secret("not_acme", path, secret)
    all_secrets = vault.list_secrets(workspace_id)
    assert len(all_secrets) == 1, "There should be exactly one secret for the workspace"
    assert (
        all_secrets[0] == path
    ), "The path of the listed secret should match the original"


@patch.dict("os.environ", {}, clear=True)
def test_delete_secret(vault_env):
    vault, workspace_id, path, secret = vault_env
    # Set a secret first
    vault.set_secret(workspace_id, path, secret)

    # Test delete_secret
    delete_result = vault.delete_secret(workspace_id, path)
    assert delete_result, "Delete secret should return True"

    # Verify secret is deleted
    retrieved_secret = vault.get_secret(workspace_id, path)
    assert retrieved_secret is None, "Retrieved secret should be None after deletion"


@patch.dict("os.environ", {}, clear=True)
def test_delete_non_existent_secret(vault_env):
    vault, workspace_id, path, secret = vault_env
    # Test delete_secret on a non-existent secret
    try:
        vault.delete_secret(workspace_id, path)
        assert False, "Expected an exception for deleting a non-existent secret"
    except Exception as e:
        assert path in str(
            e
        ), "The exception message should contain the path of the non-existent secret"
