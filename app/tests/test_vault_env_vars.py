import unittest
from unittest.mock import patch

from app.vault_env_vars import EnvVarVault


class TestEnvVarVault(unittest.TestCase):
    def setUp(self):
        self.vault = EnvVarVault()
        self.org_id = "acme"
        self.path = "test_path"
        self.secret = "secret_value"

    @patch.dict("os.environ", {}, clear=True)
    def test_set_get_secret(self):
        # Test set_secret
        result = self.vault.set_secret(self.org_id, self.path, self.secret)
        self.assertTrue(result)

        # Test get_secret
        retrieved_secret = self.vault.get_secret(self.org_id, self.path)
        self.assertEqual(retrieved_secret, self.secret)

    @patch.dict("os.environ", {}, clear=True)
    def test_delete_secret(self):
        # Set a secret first
        self.vault.set_secret(self.org_id, self.path, self.secret)

        # Test delete_secret
        delete_result = self.vault.delete_secret(self.org_id, self.path)
        self.assertTrue(delete_result)

        # Verify secret is deleted
        retrieved_secret = self.vault.get_secret(self.org_id, self.path)
        self.assertIsNone(retrieved_secret)

    @patch.dict("os.environ", {}, clear=True)
    def test_delete_non_existent_secret(self):
        # Test delete_secret on a non-existent secret
        delete_result = self.vault.delete_secret(self.org_id, self.path)
        self.assertFalse(delete_result)


if __name__ == "__main__":
    unittest.main()
