import os

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
