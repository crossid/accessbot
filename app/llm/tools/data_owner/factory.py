from typing import Any

from app.llm.tools.data_owner.mock import MockImpl
from app.models import User, Workspace
from app.services import factory_user_store
from app.vault_utils import resolve_ws_config_secrets

from ..consts import DATAOWNER_CONFIG_KEY, DIRECTORIES_KEY
from .iface import DataOwnerInterface
from .okta import OktaImpl


def DataOwnerFactory(type: str, config: dict[str, Any]) -> DataOwnerInterface:
    match type:
        case "okta":
            return OktaImpl(**config)
        case "_mock_":
            return MockImpl(**config)

    raise ValueError(type)


def get_def_do(do_email: str) -> User:
    if do_email is None or do_email == "":
        raise ValueError("default data owner email is not set")

    user_store = factory_user_store()
    owner = user_store.get_by_email(email=do_email)
    return owner


async def get_data_owner(
    ws: Workspace, app_name: str, directory: str, **kwargs
) -> User:
    default_do_email = ws.config.get(DATAOWNER_CONFIG_KEY, None)

    do_config = (
        ws.config.get(DIRECTORIES_KEY, {})
        .get(directory, {})
        .get(DATAOWNER_CONFIG_KEY, None)
    )

    if do_config is None:
        return get_def_do(do_email=default_do_email)

    try:
        resolved_config = resolve_ws_config_secrets(
            workspace_id=ws.id, config=do_config["config"]
        )
        doFactory = DataOwnerFactory(
            type=do_config["type"],
            config=resolved_config,
        )
        owner = await doFactory.get_data_owner(app_name=app_name, **kwargs)
        if owner is None:
            raise ValueError(
                f"could not find data owner for  [{directory}|{app_name}|{kwargs}]"
            )

        return owner
    except Exception:
        # TODO: logger
        return get_def_do(do_email=default_do_email)
