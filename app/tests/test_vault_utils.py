from unittest.mock import MagicMock

import pytest

from app.vault_utils import resolve_secrets


@pytest.fixture
def secret_resolver():
    mock_resolver = MagicMock()
    mock_resolver.get_secret.side_effect = lambda path: f"secret-value-for-{path}"
    return mock_resolver


def test_resolve_secrets(secret_resolver):
    config = {
        "database": {
            "host": "localhost",
            "port": 3306,
            "name": "app_db",
            "password": "vault://database/credentials/db_password",
        },
        "api": {
            "key": "vault://api/credentials/api_key",
            "endpoints": [
                "vault://endpoint/service1",
                {"url": "vault://endpoint/service2"},
            ],
        },
        "non_secret_data": "This should remain unchanged",
    }

    expected = {
        "database": {
            "host": "localhost",
            "port": 3306,
            "name": "app_db",
            "password": "secret-value-for-database/credentials/db_password",
        },
        "api": {
            "key": "secret-value-for-api/credentials/api_key",
            "endpoints": [
                "secret-value-for-endpoint/service1",
                {"url": "secret-value-for-endpoint/service2"},
            ],
        },
        "non_secret_data": "This should remain unchanged",
    }

    resolved_config = resolve_secrets(config, secret_resolver)
    assert (
        resolved_config == expected
    ), "Resolved config does not match the expected output"

    # Test calls to secret_resolver.get_secret
    expected_calls = [
        (("database/credentials/db_password",),),
        (("api/credentials/api_key",),),
        (("endpoint/service1",),),
        (("endpoint/service2",),),
    ]
    secret_resolver.get_secret.assert_has_calls(expected_calls, any_order=True)
