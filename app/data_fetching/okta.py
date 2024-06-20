from typing import List

from app.data_fetching.iface import DataFetcherInterface
from app.data_fetching.utils import Doc


def okta_group_to_doc(id, name, description, dir_name, apps) -> Doc:
    ra = [
        f"**role id**: {id}",
        f"**role name**: {name}",
        f"**role description**: {description}",
    ]
    content = "\n".join(ra)
    return Doc(directory=dir_name, content=content, external_id="okta", apps=apps)


class DFOktaImpl(DataFetcherInterface):
    def __init__(self, tenant, token) -> None:
        try:
            from okta.client import Client as OktaClient
        except ImportError:
            raise ImportError(
                "Could not import atlassian package. "
                "Please install it with `pip install okta`."
            )

        config = {"orgUrl": f"https://{tenant}", "token": token}
        self.client = OktaClient(config)

    async def fetch_content(self, dir_name: str) -> List[Doc]:
        groups, resp, err = await self.client.list_groups()
        if err is not None:
            raise ValueError(f"error while fetching groups: {err}")

        groups_md = []
        while True:
            for group in groups:
                gapps, _, err = await self.client.list_assigned_applications_for_group(
                    groupId=group.id
                )

                # TODO: this is a bit weird, and we'll have to think about this
                apps = [a.label.lower().replace(" ", "_") for a in gapps]

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

        return groups_md
