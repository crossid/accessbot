from app.llm.tools.user_data.iface import UserDataInterface
from app.llm.tools.user_data.mock import MockImpl
from app.llm.tools.user_data.webhook import WebhookImpl
from app.models import Directory, Workspace
from app.vault_utils import resolve_ws_config_secrets


def GetUserDataFactory(workspace: Workspace, directory: Directory) -> UserDataInterface:
    if directory.read_config is None:
        return None

    read_type = directory.read_config["type"]
    read_config = directory.read_config["config"]
    resolved_config = resolve_ws_config_secrets(
        workspace_id=workspace.id, config=read_config
    )

    match read_type:
        case "webhook":
            return WebhookImpl(**resolved_config)
        case "_mock_":
            return MockImpl(**resolved_config)

    raise ValueError(
        f"could not instantiate get user data factory for type: {read_type}"
    )
