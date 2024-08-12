import base64
from cProfile import label
from typing import List

from fastapi import HTTPException
from kubernetes import client, config
from regex import D

from app.vault.api import VaultAPI


class KubernetesVaultImpl(VaultAPI):
    def __init__(self, namespace, config_file) -> None:
        # Load the Kubernetes configuration
        if config_file is None:
             config.load_incluster_config()  # Use this if running inside the cluster
        else:
            config.load_kube_config(config_file=config_file)
        self.core_v1_api = client.CoreV1Api()
        self.namespace = namespace

    def create_workspace_path(self, workspace_id: str, path: str) -> str:
        return f"{workspace_id.lower()}-{path}".replace("/", "--").replace("_", "-")
        # return f"{path.replace('/', '--').replace('_', '-')}"

    def getNamespace(self, workspace_id: str):
        return self.namespace if self.namespace else workspace_id

    def get_secret(self, workspace_id: str, path: str) -> str:
        secret_name = self.create_workspace_path(workspace_id, path)
        try:
            secret = self.core_v1_api.read_namespaced_secret(
                secret_name, namespace=self.getNamespace(workspace_id)
            )
            # filter only if label is workspace
            labels = secret.metadata.labels or {}
            if labels.get("workspace") != workspace_id.lower():
                raise ValueError(
                    f"Secret '{path}' not found for workspace '{workspace_id}'"
                )

            return base64.b64decode(secret.data["value"]).decode("utf-8")
        except HTTPException as e:
            if e.status_code == 404:
                raise ValueError(
                    f"Secret '{path}' not found for workspace '{workspace_id}'"
                )
            else:
                raise e

    def set_secret(self, workspace_id: str, path: str, value: str) -> bool:
        secret_name = self.create_workspace_path(workspace_id, path)
        secret_data = {"value": base64.b64encode(value.encode("utf-8")).decode("utf-8")}
        secret_body = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=secret_name, labels={"workspace": workspace_id.lower()}
            ),
            data=secret_data,
        )
        try:
            self.core_v1_api.create_namespaced_secret(
                namespace=self.getNamespace(workspace_id), body=secret_body
            )
        except HTTPException as e:
            if e.status_code == 409:
                # Secret already exists, so update it
                self.core_v1_api.patch_namespaced_secret(
                    name=secret_name, namespace=self.getNamespace(workspace_id), body=secret_body
                )
            else:
                raise e
        return True

    def delete_secret(self, workspace_id: str, path: str) -> bool:
        secret_name = self.create_workspace_path(workspace_id, path)
        try:
            self.core_v1_api.delete_namespaced_secret(
                name=secret_name, namespace=self.getNamespace(workspace_id),
            )
            return True
        except HTTPException as e:
            if e.status_code == 404:
                return True  # Secret not found, nothing to delete
            else:
                raise e

    def list_secrets(self, workspace_id: str) -> List[str]:
        label_selector = f"workspace={workspace_id.lower()}"
        secret_list = self.core_v1_api.list_namespaced_secret(
            namespace=self.getNamespace(workspace_id), label_selector=label_selector
        )
        return [secret.metadata.name for secret in secret_list.items]
