from .models import Org
from .models_stores import UserStore


class UserStoreSCIM(UserStore):
    def get_by_email(self, email: str):
        pass

    def list_orgs_for_user(self, user_id: str) -> list[Org]:
        pass
