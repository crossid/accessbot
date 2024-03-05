import unittest
from unittest.mock import MagicMock

from app.vault_utils import resolve_secrets


class TestResolveSecrets(unittest.TestCase):
    def setUp(self):
        self.secret_resolver = MagicMock()
        self.secret_resolver.get_secret.side_effect = self.mock_get_secret

    def mock_get_secret(self, path):
        return f"secret-value-for-{path}"

    def test_resolve_secrets(self):
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

        resolved_config = resolve_secrets(config, self.secret_resolver)
        self.assertEqual(resolved_config, expected)

        # Test calls to secret_resolver.get_secret
        expected_calls = [
            (("database/credentials/db_password",),),
            (("api/credentials/api_key",),),
            (("endpoint/service1",),),
            (("endpoint/service2",),),
        ]
        self.secret_resolver.get_secret.assert_has_calls(expected_calls, any_order=True)


if __name__ == "__main__":
    unittest.main()
