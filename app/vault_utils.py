from app.vault import VaultAPI

VAULT_VAR_URI = "vault://"


def resolve_secrets(config, secret_resolver):
    """
    Recursively traverses the configuration, replacing any 'vault://' placeholder with a secret.

    :param config: The configuration dictionary or a part of it.
    :param secret_resolver: An instance of a class that can fetch secrets from a vault given a path.
    :return: The configuration dictionary with secrets resolved.
    """
    if isinstance(config, dict):
        for key, value in config.items():
            config[key] = resolve_secrets(value, secret_resolver)
    elif isinstance(config, list):
        return [resolve_secrets(item, secret_resolver) for item in config]
    elif isinstance(config, str) and config.startswith(VAULT_VAR_URI):
        secret_path = config[8:]
        return secret_resolver.get_secret(secret_path)
    return config


class OrgVaultSecretResolver:
    def __init__(self, vault: VaultAPI, org_id: str):
        """
        Initializes the SecretResolver with a vault instance and organization id.

        :param vault: An instance of a class that implements the VaultInterface.
        :param org_id: The organization id to use with the vault.
        """
        self.vault = vault
        self.org_id = org_id

    def get_secret(self, path: str) -> str:
        """
        Retrieves a secret from the vault.

        :param path: The path of the secret to retrieve.
        :return: The secret value.
        """
        return self.vault.get_secret(self.org_id, path)
