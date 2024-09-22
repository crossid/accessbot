import logging
from typing import Any, Optional

from app.consts import DATAOWNER_CONFIG_KEY
from app.llm.tools.data_owner.azure import AzureImpl
from app.llm.tools.data_owner.mock import MockImpl
from app.llm.tools.data_owner.okta import OktaImpl
from app.models import Directory, User, Workspace
from app.services import factory_reg_provider, factory_user_store
from app.utils.emails.factory import EmailFactoryForWS
from app.vault_utils import resolve_ws_config_secrets

from .iface import DataOwnerInterface

logger = logging.getLogger(__name__)


def DataOwnerFactory(type: str, config: dict[str, Any]) -> DataOwnerInterface:
    match type:
        case "okta":
            return OktaImpl(**config)
        case "azure":
            return AzureImpl(**config)
        case "_mock_":
            return MockImpl(**config)

    raise ValueError(type)


def get_do(do_email: str) -> Optional[User]:
    if do_email is None or do_email == "":
        raise ValueError("default data owner email is not set")

    user_store = factory_user_store()
    owner = user_store.get_by_email(email=do_email)
    if owner is None:
        # return a user without an email to indicate the user is not registered
        return User(id="", email=do_email)

    return owner


def send_registration_email(ws: Workspace, to: str):
    reg_provider = factory_reg_provider()
    reg_params = reg_provider.get_registration_email(workspace_id=ws.id)
    email_sender = EmailFactoryForWS(ws=ws)
    try:
        _ = email_sender.send(
            from_addr=reg_params.from_addr,
            to=to,
            content=reg_params.content,
            content_type=reg_params.content_type,
            subject=reg_params.subject,
        )
    except Exception as e:
        logger.debug(f"failed to send registration email: {str(e)}")


async def get_data_owner(
    ws: Workspace,
    app_name: str,
    directory: Directory,
    should_send_registration_email=True,
    **kwargs,
) -> User:
    data_owner: Optional[User] = None
    default_do_email = ws.config.get(DATAOWNER_CONFIG_KEY, None)

    do_config = directory.data_owner_config

    if do_config is not None:
        try:
            resolved_config = resolve_ws_config_secrets(
                workspace_id=ws.id, config=do_config["config"]
            )
            doFactory = DataOwnerFactory(
                type=do_config["type"],
                config=resolved_config,
            )
            owner_email = await doFactory.get_data_owner(app_name=app_name, **kwargs)
            if owner_email is None:
                raise ValueError(
                    f"could not find data owner for  [{directory}|{app_name}|{kwargs}]"
                )

            data_owner = get_do(do_email=owner_email)
        except Exception as e:
            logger.debug(f"Could not find data owner: {str(e)}")
            data_owner = get_do(do_email=default_do_email)
    else:
        data_owner = get_do(do_email=default_do_email)

    if data_owner.id == "" and should_send_registration_email:
        # send registration email to data owner
        send_registration_email(ws=ws, to=data_owner.email)

    return data_owner
