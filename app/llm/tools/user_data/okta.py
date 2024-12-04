import logging
from typing import Any, List

from .iface import UserAccess, UserDataInterface

logger = logging.getLogger(__name__)


def get_relevant_attributes() -> List[str]:
    security_relevant_attributes = [
        # Primary attributes
        "department",
        "division",
        "organization",
        "title",
        "manager",
        "managerId",
        "userType",
        "costCenter",
        # Secondary attributes
        "employeeNumber",
        "countryCode",
        "locale",
        "email",
        "login",
        # so we'll have it in the metadata
        "displayName",
    ]
    return security_relevant_attributes


def okta_user_to_dict(user) -> dict[str, Any]:
    user_data = {"id": user.id}
    for attr in get_relevant_attributes():
        user_attr = getattr(user.profile, attr)
        if user_attr is not None:
            user_data[attr] = user_attr

    return user_data


class OktaUserDataImpl(UserDataInterface):
    def __init__(self, tenant: str, token: str) -> None:
        try:
            from okta.client import Client as OktaClient

        except ImportError:
            raise ImportError(
                "Could not import okta package. "
                "Please install it with `pip install okta`."
            )

        config = {"orgUrl": f"https://{tenant}", "token": token}
        self.client = OktaClient(config)

    async def list_users_data(self, **kwargs) -> List[dict[str, Any]]:
        users, resp, err = await self.client.list_users()
        if err:
            raise ValueError(f"Error fetching okta users: {err.error_summary}")

        result = []
        for user in users:
            result.append(okta_user_to_dict(user))

        return result

    async def get_user_data(self, user_email: str, **kwargs) -> dict[str, Any]:
        qp = {"search": f'profile.email eq "{user_email}"'}
        users, resp, err = await self.client.list_users(query_params=qp)
        if err:
            raise ValueError(f"Error fetching okta user data: {err.error_summary}")

        if not users:
            raise ValueError(
                f"Error fetching okta user data: no user wih email {user_email}"
            )

        user = users[0]
        return okta_user_to_dict(user)

    async def get_user_access(
        self, user_email: str, app_names: list[str] = [], **kwargs
    ) -> dict[str, list[UserAccess]]:
        # First get the user
        qp = {"search": f'profile.email eq "{user_email}"'}
        users, resp, err = await self.client.list_users(query_params=qp)
        if err:
            raise ValueError(f"Error fetching okta user: {err.error_summary}")

        if err or not users:
            return {}

        user = users[0]

        # Get user's groups
        groups, resp, err = await self.client.list_user_groups(user.id)
        if err:
            raise ValueError(f"Error fetching user groups: {err}")

        # Initialize result dictionary
        access_by_app = {}

        # Process each group
        for group in groups:
            # Get applications assigned to this group
            apps, _, err = await self.client.list_assigned_applications_for_group(
                group.id
            )
            if err:
                logger.warning(f"Error fetching apps for group {group.id}: {err}")
                continue

            for app in apps:
                app_name = app.name.replace(
                    "_", ""
                )  # Match create_app_name from DFOktaImpl

                # Skip if app_names filter is provided and this app isn't in it
                if app_names and app_name not in app_names:
                    continue

                # Create UserAccess object for this group's access to the app
                access = UserAccess(
                    id=group.id,
                    name=group.profile.name,
                    description=group.profile.description,
                )

                if app_name not in access_by_app:
                    access_by_app[app_name] = []
                access_by_app[app_name].append(access)

        return access_by_app
