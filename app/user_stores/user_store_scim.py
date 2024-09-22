from app.models_stores import UserStore


class UserStoreSCIM(UserStore):
    def get_by_email(self, email: str):
        pass

    def list_workspaces_for_user(self, user_id: str) -> list[str]:
        pass

    def add_user_to_workspace(self, user_id: str, workspace_id: str):
        pass
