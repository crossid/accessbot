import os
import re
from typing import List

from .api import VaultAPI


class EnvVarVault(VaultAPI):
    def get_secret(self, workspace_id: str, path: str) -> str:
        # Create a unique key for each secret
        key = f"{workspace_id}_{path}".upper()
        return os.environ.get(key)

    def set_secret(self, workspace_id: str, path: str, value: str) -> bool:
        key = f"{workspace_id}_{path}".upper()
        os.environ[key] = value
        return True

    def delete_secret(self, workspace_id: str, path: str) -> bool:
        key = f"{workspace_id}_{path}".upper()
        # delete if anything to delete
        if key in os.environ:
            del os.environ[key]
            return True

        raise ValueError(f"could not find path {path}")

    def list_secrets(self, workspace_id: str) -> List[str]:
        ws_keys = []
        for key in os.environ:
            if key.startswith(workspace_id.upper()):
                secret_name = re.sub(f"^{workspace_id}_", "", key, flags=re.IGNORECASE)
                ws_keys.append(secret_name.lower())

        return ws_keys
