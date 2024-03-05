import os
import re
from typing import List

from .vault import VaultAPI


class EnvVarVault(VaultAPI):
    def get_secret(self, org_id: str, path: str) -> str:
        # Create a unique key for each secret
        key = f"{org_id}_{path}".upper()
        return os.environ.get(key)

    def set_secret(self, org_id: str, path: str, value: str) -> bool:
        try:
            key = f"{org_id}_{path}".upper()
            os.environ[key] = value
            return True
        except Exception as e:
            print(f"Error setting secret: {e}")
            return False

    def delete_secret(self, org_id: str, path: str) -> bool:
        try:
            key = f"{org_id}_{path}".upper()
            if key in os.environ:
                del os.environ[key]
                return True
            return False
        except Exception as e:
            print(f"Error deleting secret: {e}")
            return False

    def list_secrets(self, org_id: str) -> List[str]:
        org_keys = []
        for key in os.environ:
            if key.startswith(org_id.upper()):
                secret_name = re.sub(f"^{org_id}_", "", key, flags=re.IGNORECASE)
                org_keys.append(secret_name.lower())

        return org_keys
