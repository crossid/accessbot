from app.models import Org
from app.models_facade import UserStore


class UserStoreSCIM(UserStore):
    def get_by_email(self, email: str):
        pass

    def list_orgs_for_user(self, user_id: str) -> list[Org]:
        pass
