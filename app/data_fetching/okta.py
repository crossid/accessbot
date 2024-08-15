import logging
from typing import List

from app.data_fetching.iface import DataFetcherInterface
from app.data_fetching.utils import Doc
from app.models import Application
from app.services import factory_app_store
from app.sql import SQLAlchemyTransactionContext

logger = logging.getLogger(__name__)


def okta_group_to_doc(id, name, description, dir_name, apps) -> Doc:
    ra = [
        f"**role id**: {id}",
        f"**role name**: {name}",
        f"**role description**: {description}",
    ]
    content = "\n".join(ra)
    return Doc(
        directory=dir_name,
        display_name=name,
        content=content,
        external_id=id,
        apps=apps,
    )


def create_app_name(name: str):
    return name.replace("_", "")


class DFOktaImpl(DataFetcherInterface):
    def __init__(self, workspace_id, tenant, token) -> None:
        try:
            from okta.client import Client as OktaClient
        except ImportError:
            raise ImportError(
                "Could not import atlassian package. "
                "Please install it with `pip install okta`."
            )

        config = {"orgUrl": f"https://{tenant}", "token": token}
        self.client = OktaClient(config)
        self.workspace_id = workspace_id

    async def fetch_content(self, dir_name: str, **kwargs) -> List[Doc]:
        groups, resp, err = await self.client.list_groups(
            query_params={"expand": "stats"}
        )
        if err is not None:
            raise ValueError(f"error while fetching groups: {err}")

        groups_md = []
        all_apps = set()
        while True:
            for group in groups:
                if group.embedded.get("stats", {}).get("appsCount", 0) == 0:
                    continue

                gapps, _, err = await self.client.list_assigned_applications_for_group(
                    groupId=group.id
                )

                # apps must be alphanumeric only
                apps = [create_app_name(a.name) for a in gapps]
                all_apps.update(gapps)

                gmd = okta_group_to_doc(
                    id=group.id,
                    name=group.profile.name,
                    description=group.profile.description,
                    dir_name=dir_name,
                    apps=apps,
                )
                groups_md.append(gmd)
            if resp.has_next():
                groups, err = await resp.next()
                if err is not None:
                    raise ValueError(f"error while fetching groups: {err}")
            else:
                break

        if kwargs.get("create_apps"):
            app_store = factory_app_store()
            with SQLAlchemyTransactionContext().manage() as tx_context:
                known_apps, _ = app_store.list(
                    workspace_id=self.workspace_id,
                    limit=1000,
                    tx_context=tx_context,
                    projection=["name"],
                )
                known_apps_names = [ka.name for ka in known_apps]
                for gapp in all_apps:
                    gapp_name = create_app_name(gapp.name)
                    if gapp_name not in known_apps_names:
                        a = Application(
                            name=gapp_name,
                            aliases=[gapp.label],
                            workspace_id=self.workspace_id,
                        )
                        app_store.insert(app=a, tx_context=tx_context)

        return groups_md
