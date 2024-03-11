from app.services import factory_user_store
from app.utils.boundary_client import Client as BoundaryClient
from app.utils.boundary_client import break_role_id

from .iface import ProvisionInterface


class BoundaryImpl(ProvisionInterface):
    client: BoundaryClient

    def __init__(self, host, auth_method_id, attributes) -> None:
        client = BoundaryClient(host=host)
        client.auth(auth_method_id=auth_method_id, attributes=attributes)
        self.client = client

    def get_user_of_sub_or_email(self, sub: str, email: str):
        auth_methods = self.client.list_resource(
            url="auth-methods",
            params={
                "scope_id": "global",
                "recursive": True,
            },
        )

        account_params = {
            "scope_id": "global",
            "recursive": True,
            "filter": f"item.attributes.subject matches {sub} or item.attributes.email matches {email}",
            "page_size": 1,
        }

        for am in auth_methods.items:
            account_params["auth_method_id"] = am["id"]
            accounts_resp = self.client.list_resource(
                url="accounts", params=account_params
            )
            if len(accounts_resp.items) > 0:
                account = accounts_resp.items[0]

        if account is None:
            raise ValueError("could not find account for subject or email")

        userParams = {
            "scope_id": "global",
            "recursive": True,
        }

        user_of_account = None
        users_resp = self.client.list_resource(url="users", params=userParams)
        while user_of_account is None:
            for u in users_resp.items:
                user_id = u["id"]
                user_resp = self.client.get_resource(f"/users/{user_id}")
                user = user_resp.item
                user_accounts = user.get("accounts", [])
                for a in user_accounts:
                    if a["id"] == account["id"]:
                        user_of_account = user
                        break

            if users_resp.has_next():
                users_resp = users_resp.get_next()
            else:
                break

        if user_of_account is None:
            raise ValueError("could not find principal for provided account")

        return user_of_account

    def add_user_to_role(self, user_id: str, role_id: str):
        role = self.client.get_resource(f"/roles/{role_id}")
        version = role.item["version"]
        self.client.add_principal(user_id=user_id, role_id=role_id, version=version)

    async def approve_request(self, requester_email: str, **kwargs) -> bool:
        role_name = kwargs.get("role_name", None)
        if role_name is None:
            raise ValueError("role_name must be set for boundary provisioning")
        role = break_role_id(role_id=role_name)
        user_store = factory_user_store()
        user = user_store.get_by_email(email=requester_email)
        if user is None:
            raise ValueError(f"no user found for email: {requester_email}")

        boundary_user = self.get_user_of_sub_or_email(
            sub=user.id, email=requester_email
        )

        self.add_user_to_role(user_id=boundary_user["id"], role_id=role.role_id)

        return True
