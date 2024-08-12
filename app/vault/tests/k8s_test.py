import base64
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.vault.k8s import KubernetesVaultImpl


class TestKubernetesVaultImpl(unittest.TestCase):
    @patch("kubernetes.client.CoreV1Api")
    @patch("kubernetes.config.load_incluster_config")
    def setUp(self, mock_load_incluster_config, MockCoreV1Api):
        self.mock_core_v1_api = MockCoreV1Api.return_value
        self.kubernetes_vault = KubernetesVaultImpl()

    def test_create_workspace_path(self):
        path = self.kubernetes_vault.create_workspace_path("workspace1", "secret_path")
        self.assertEqual(path, "workspace1-secret-path")

    def test_get_secret_success(self):
        mock_secret = MagicMock()
        mock_secret.data = {
            "value": base64.b64encode(b"my_secret_value").decode("utf-8"),
        }
        mock_secret.metadata.labels = {"workspace": "workspace1"}
        self.mock_core_v1_api.read_namespaced_secret.return_value = mock_secret

        secret_value = self.kubernetes_vault.get_secret("workspace1", "secret_path")
        self.assertEqual(secret_value, "my_secret_value")

    def test_get_secret_not_found(self):
        self.mock_core_v1_api.read_namespaced_secret.side_effect = HTTPException(
            status_code=404
        )

        with self.assertRaises(ValueError) as context:
            self.kubernetes_vault.get_secret("workspace1", "secret_path")

        self.assertTrue(
            "Secret 'secret_path' not found for workspace 'workspace1'"
            in str(context.exception)
        )

    def test_set_secret_create(self):
        self.mock_core_v1_api.create_namespaced_secret.return_value = None
        success = self.kubernetes_vault.set_secret(
            "workspace1", "secret_path", "my_secret_value"
        )

        self.assertTrue(success)
        self.mock_core_v1_api.create_namespaced_secret.assert_called_once()

    def test_set_secret_update(self):
        self.mock_core_v1_api.create_namespaced_secret.side_effect = HTTPException(
            status_code=409
        )
        self.mock_core_v1_api.patch_namespaced_secret.return_value = None

        success = self.kubernetes_vault.set_secret(
            "workspace1", "secret_path", "my_secret_value"
        )

        self.assertTrue(success)
        self.mock_core_v1_api.patch_namespaced_secret.assert_called_once()

    def test_delete_secret_success(self):
        self.mock_core_v1_api.delete_namespaced_secret.return_value = None

        success = self.kubernetes_vault.delete_secret("workspace1", "secret_path")

        self.assertTrue(success)
        self.mock_core_v1_api.delete_namespaced_secret.assert_called_once()

    def test_delete_secret_not_found(self):
        self.mock_core_v1_api.delete_namespaced_secret.side_effect = HTTPException(
            status_code=404
        )

        success = self.kubernetes_vault.delete_secret("workspace1", "secret_path")

        self.assertTrue(success)
        self.mock_core_v1_api.delete_namespaced_secret.assert_called_once()

    def test_list_secrets(self):
        mock_secret_1 = MagicMock()
        mock_secret_1.metadata.name = "workspace1-secret-1"
        mock_secret_2 = MagicMock()
        mock_secret_2.metadata.name = "workspace1-secret-2"

        self.mock_core_v1_api.list_namespaced_secret.return_value.items = [
            mock_secret_1,
            mock_secret_2,
        ]

        secrets = self.kubernetes_vault.list_secrets("workspace1")

        self.assertEqual(secrets, ["workspace1-secret-1", "workspace1-secret-2"])
        self.mock_core_v1_api.list_namespaced_secret.assert_called_once()


if __name__ == "__main__":
    unittest.main()
