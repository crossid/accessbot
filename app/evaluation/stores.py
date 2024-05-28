from typing import Any, Optional

from app.llm.tools.consts import DATAOWNER_CONFIG_KEY, TICKET_SYSTEM_CONFIG_KEY
from fastapi import BackgroundTasks

from app.models import (
    Application,
    ChatMessage,
    Conversation,
    CurrentUser,
    User,
    Workspace,
)
from app.models_stores import (
    ApplicationStore,
    ChatMessageStore,
    ConversationStore,
    TransactionContext,
    UserStore,
    WorkspaceStatuses,
    WorkspaceStore,
)

SINGLE_USER_EMAIL = "jondoe@foobar.com"


class WorkspaceStoreMock(WorkspaceStore):
    def get_by_id(
        self, workspace_id: str, tx_context: TransactionContext
    ) -> Optional[Workspace]:
        config: dict[str, Any] = {
            DATAOWNER_CONFIG_KEY:SINGLE_USER_EMAIL,
            TICKET_SYSTEM_CONFIG_KEY: {"type": "_mock_", "config": {}}
        }
        return Workspace(
            id=workspace_id,
            external_id="external",
            display_name="mock",
            status=WorkspaceStatuses.active,
            created_by=SINGLE_USER_EMAIL,
            config=config,
        )

    def insert(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ) -> Workspace:
        pass

    def update(
        self,
        workspace: Workspace,
        tx_context: TransactionContext,
    ) -> Workspace:
        pass

    def delete(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ):
        pass


class ConversationStoreMock(ConversationStore):
    def get_by_id(
        self,
        workspace_id: str,
        conversation_id: str,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ):
        pass

    def get_by_external_id(
        self,
        workspace_id: str,
        external_id: str,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ) -> Optional[Conversation]:
        pass

    def list(
        self,
        workspace_id: str,
        tx_context: TransactionContext,
        limit: int = 10,
        offset: int = 0,
        filters: dict[str, Any] = None,
        links: Optional[list[str]] = None,
    ) -> tuple[list[Conversation], int]:
        return [], 0

    def insert(
        self, conversation: Conversation, tx_context: TransactionContext
    ) -> Conversation:
        pass

    def update(
        self,
        workspace_id: str,
        conversation_id: str,
        updates: dict[str, Any],
        tx_context: TransactionContext,
    ) -> Conversation:
        pass

    def delete_for_workspace(
        self, workspace_id: str, tx_context: TransactionContext = None
    ):
        pass


class ChatMessageStoreMock(ChatMessageStore):
    def list(
        self, filter: None, offset=0, limit=10, tx_context: TransactionContext = None
    ):
        pass

    def get_by_id(
        self, id: str, tx_context: TransactionContext
    ) -> Optional[ChatMessage]:
        pass

    def insert(
        self, message: ChatMessage, tx_context: TransactionContext
    ) -> ChatMessage:
        pass

    def delete(self, filter=None, tx_context: TransactionContext = None):
        pass

    def delete_for_workspace(
        self, workspace_id: str, tx_context: TransactionContext = None
    ):
        pass


class ApplicationStoreMock(ApplicationStore):
    application = Application(
        id="1",
        workspace_id="1",
        display_name="fooquery",
        aliases=["fquery", "fq"],
        extra_instructions="bla bla bla",
        provision_schema={},
    )

    def list(
        self,
        workspace_id: str,
        filters: dict[str, Any] = None,
        offset=0,
        limit=10,
        tx_context: TransactionContext = None,
    ) -> list[Application]:
        return [self.application]

    def get_by_id(
        self, app_id: str, workspace_id: str, tx_context: TransactionContext
    ) -> Optional[Application]:
        return self.application

    def get_by_name(
        self, app_name: str, workspace_id: str, tx_context: TransactionContext
    ) -> Optional[Application]:
        return self.application

    def insert(self, app: Application, tx_context: TransactionContext) -> Application:
        pass

    def delete(
        self,
        workspace_id: str,
        app_id: str,
        tx_context: TransactionContext = None,
    ):
        pass

    def delete_for_workspace(
        self, workspace_id: str, tx_context: TransactionContext = None
    ) -> None:
        pass

    def update(self, **kwargs):
        pass


class UserStoreMock(UserStore):
    def get_by_email(self, email: str) -> Optional[User]:
        return User(
            id="1", email=SINGLE_USER_EMAIL, full_name="Jon Doe", disabled=False
        )

    def list_workspaces_for_user(self, user_id: str) -> list[str]:
        return []
