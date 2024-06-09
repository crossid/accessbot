from app.llm.tools.access_data.iface import AccessDataInterface
from app.llm.tools.access_data.mock import MockImpl
from app.models import Directory, Workspace
from app.vault_utils import resolve_ws_config_secrets


def GetAccessDataFactory(
    workspace: Workspace, directory: Directory
) -> AccessDataInterface:
    if directory.read_config is None:
        return None

    read_type = directory.read_config["type"]
    read_config = directory.read_config["config"]
    resolved_config = resolve_ws_config_secrets(
        workspace_id=workspace.id, config=read_config
    )

    match read_type:
        case "_mock_":
            return MockImpl(**resolved_config)

    raise ValueError(
        f"could not instantiate get access data factory for type: {read_type}"
    )
