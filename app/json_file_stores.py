import json
import os
from typing import Any, Optional

from app.models import User
from app.models_stores import UserStore
from app.settings import settings


class UserStoreFromJsonFile(UserStore):
    _file_path = os.path.abspath(settings.USER_STORE_FILE_PATH)

    def _dict_to_user(self, user: dict[str, Any]):
        return User(
            id=user.get("id"),
            email=user.get("email"),
            full_name=user.get("name"),
            disabled=user.get("blocked", False),
        )

    def get_by_email(self, email: str) -> Optional[User]:
        with open(self._file_path, "r") as file:
            store = json.load(file)
            store_user = store["users"].get(email, None)
            if store_user is None:
                return None

            return self._dict_to_user(store_user)

    def list_workspaces_for_user(self, user_id: str) -> list[str]:
        with open(self._file_path, "r") as file:
            store = json.load(file)
            user = next(
                filter(lambda x: x["id"] == user_id, store["users"].values()), None
            )
            if user is None:
                raise ValueError(f"Could not find user: {user_id}")

            return user.get("memberOf", [])
