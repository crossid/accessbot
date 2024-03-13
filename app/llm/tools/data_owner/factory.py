from typing import Any

from app.models import User, Workspace
from app.services import factory_user_store
from app.vault_utils import resolve_ws_config_secrets

from ..consts import DATAOWNER_CONFIG_KEY
from .iface import DataOwnerInterface
from .okta import OktaImpl


def DataOwnerFactory(type: str, config: dict[str, Any]) -> DataOwnerInterface:
    match type:
        case "okta":
            return OktaImpl(**config)

    raise ValueError(type)


async def get_data_owner(ws: Workspace, role_name: str) -> User:
    directory_role_name = role_name.split("/")
    if len(directory_role_name) < 3:
        raise ValueError("No directory provided")
    directory = directory_role_name[0]
    role_name = directory_role_name.pop()

    do_config = ws.config[DATAOWNER_CONFIG_KEY]
    if directory in do_config and "type" in do_config[directory]:
        do_config = do_config[directory]
        config = do_config["config"]
        resolved_config = resolve_ws_config_secrets(workspace_id=ws.id, config=config)
        doFactory = DataOwnerFactory(
            type=ws.config[DATAOWNER_CONFIG_KEY][directory]["type"],
            config=resolved_config,
        )
        owner = await doFactory.get_data_owner(rolename=role_name)
    else:
        user_store = factory_user_store()
        do_email = do_config["default_data_owner_email"]
        owner = user_store.get_by_email(email=do_email)

    return owner
