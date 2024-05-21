import json
import os
from typing import Any, Optional

from app.models import Application, User, Workspace
from app.models_stores import ApplicationStore, UserStore


class UserStoreFromJsonFile(UserStore):
    _file_path = os.path.abspath("tmp/data.json")

    def _dict_to_user(self, user: dict[str, Any]):
        return User(
            id=user.get("id"),
            email=user.get("email"),
            full_name=user.get("name"),
            disabled=user.get("blocked", False),
        )

    def _dict_to_ws(self, ws: dict[str, Any]):
        return Workspace(
            id=ws.get("id"),
            display_name=ws.get("display_name"),
            external_id=ws.get("external_id"),
            config=ws.get("config", {}),
            created_by=ws.get("created_by"),
        )

    def get_by_email(self, email: str) -> Optional[User]:
        with open(self._file_path, "r") as file:
            store = json.load(file)
            store_user = store["users"].get(email, None)
            if store_user is None:
                return None

            return self._dict_to_user(store_user)

    def list_workspaces_for_user(self, user_id: str) -> list[Workspace]:
        with open(self._file_path, "r") as file:
            store = json.load(file)
            user = next(
                filter(lambda x: x["id"] == user_id, store["users"].values()), None
            )
            if user is None:
                raise ValueError(f"Could not find user: {user_id}")

            user_wss = []
            for wss_id in user.get("memberOf", []):
                ws = store["wss"].get(wss_id, None)
                if ws is not None:
                    user_wss.append(self._dict_to_ws(ws))

            return user_wss


class ApplicationStoreFromJsonFile(ApplicationStore):
    _file_path = os.path.abspath("tmp/data.json")

    def _dict_to_app(self, app: dict[str, Any]):
        return Application(
            id=app.get("id"),
            workspace_id=app.get("workspace_id"),
            display_name=app.get("display_name"),
            aliases=app.get("aliases"),
            extra_instructions=app.get("extra_instructions"),
            provision_schema=app.get("provision_schema"),
        )

    def list(self, workspace_id: str, filter=None, offset=0, limit=10, tx_context=None):
        with open(self._file_path, "r") as file:
            store = json.load(file)
            return [
                self._dict_to_app(app)
                for app in store["apps"].values()
                if app["workspace_id"] == workspace_id
            ]

    def get_by_id(self, workspace_id: str, app_id: str, tx_context=None):
        with open(self._file_path, "r") as file:
            store = json.load(file)
            return self._dict_to_app(store["apps"][app_id])

    def insert(self, app: Application, tx_context=None) -> Application:
        pass

    def delete(self, workspace_id: str, filter=None, tx_context=None):
        pass

    def delete_for_workspace(self, workspace_id: str, tx_context=None) -> None:
        pass

    def update(**kwargs):
        pass

    def get_by_name(**kwargs):
        pass
