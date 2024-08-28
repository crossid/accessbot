from typing import Any

from app.llm.tools.provision.webhook import WebhookImpl
from app.vault_utils import resolve_ws_config_secrets

from .azure import AzureImpl
from .boundary import BoundaryImpl
from .iface import ProvisionInterface
from .mock import MockImpl
from .okta import OktaImpl


def ProvisionerFactory(
    workspace_id: str, type: str, config: dict[str, Any]
) -> ProvisionInterface:
    resolved_config = resolve_ws_config_secrets(
        workspace_id=workspace_id, config=config
    )

    match type:
        case "_mock_":
            return MockImpl(**resolved_config)
        case "okta":
            return OktaImpl(**resolved_config)
        case "boundary":
            return BoundaryImpl(**resolved_config)
        case "azure":
            return AzureImpl(**resolved_config)
        case "webhook":
            return WebhookImpl(**resolved_config)

    raise ValueError(f"could not instantiate provision factory for type: {type}")
