from abc import ABC, abstractmethod
from typing import Any, Optional

from fastapi import BackgroundTasks

from .models import (
    ChatMessage,
    Conversation,
    CurrentUser,
    User,
    Workspace,
    WorkspaceStatuses,
)
from .tx import TransactionContext


class WorkspaceStore(ABC):
    @abstractmethod
    def get_by_id(
        self, workspace_id: str, tx_context: TransactionContext
    ) -> Optional[Workspace]:
        pass

    @abstractmethod
    def insert(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ) -> Workspace:
        pass

    @abstractmethod
    def update(
        self,
        workspace: Workspace,
        tx_context: TransactionContext,
    ) -> Workspace:
        pass

    @abstractmethod
    def delete(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ):
        pass


class WorkspaceStoreHooks(ABC):
    @abstractmethod
    def pre_insert(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ):
        pass

    @abstractmethod
    def pre_delete(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ):
        pass


# This is here just because the injector for some reason is not handling Optional injection
class WorkspaceStoreHooksPass(WorkspaceStoreHooks):
    def pre_insert(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ):
        workspace.status = WorkspaceStatuses.active

    def pre_delete(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ):
        pass


class WorkspaceStoreProxy:
    def __init__(self, store: WorkspaceStore, hooks: WorkspaceStoreHooks):
        self._store = store
        self._hooks = hooks

    def get_by_id(
        self, workspace_id: str, tx_context: TransactionContext
    ) -> Optional[Workspace]:
        return self._store.get_by_id(workspace_id, tx_context)

    def insert(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ) -> Workspace:
        if self._hooks:
            self._hooks.pre_insert(
                workspace=workspace,
                current_user=current_user,
                background_tasks=background_tasks,
                tx_context=tx_context,
            )
        return self._store.insert(
            workspace=workspace,
            current_user=current_user,
            background_tasks=background_tasks,
            tx_context=tx_context,
        )

    def update(
        self,
        workspace: Workspace,
        tx_context: TransactionContext,
    ) -> Workspace:
        return self._store.update(workspace=workspace, tx_context=tx_context)

    def delete(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ):
        if self._hooks:
            self._hooks.pre_delete(
                workspace=workspace,
                current_user=current_user,
                background_tasks=background_tasks,
                tx_context=tx_context,
            )
        return self._store.delete(
            workspace=workspace,
            current_user=current_user,
            background_tasks=background_tasks,
            tx_context=tx_context,
        )


class UserStore(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def list_workspaces_for_user(self, user_id: str) -> list[Workspace]:
        pass


class ConversationStore(ABC):
    @abstractmethod
    def get_by_id(
        self,
        workspace_id: str,
        conversation_id: str,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ) -> Optional[Conversation]:
        pass

    @abstractmethod
    def get_by_external_id(
        self,
        workspace_id: str,
        external_id: str,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ) -> Optional[Conversation]:
        pass

    @abstractmethod
    def list(
        self,
        workspace_id: str,
        tx_context: TransactionContext,
        limit: int = 10,
        offset: int = 0,
        filters: dict[str, Any] = None,
        links: Optional[list[str]] = None,
    ) -> list[Conversation]:
        pass

    @abstractmethod
    def insert(
        self, conversation: Conversation, tx_context: TransactionContext
    ) -> Conversation:
        pass

    @abstractmethod
    def delete_for_workspace(
        self, workspace_id: str, tx_context: TransactionContext = None
    ) -> None:
        pass


class ChatMessageStore(ABC):
    @abstractmethod
    def list(
        self, filter=None, offset=0, limit=10, tx_context: TransactionContext = None
    ):
        pass

    @abstractmethod
    def get_by_id(self, message_id: str, tx_context: TransactionContext):
        pass

    @abstractmethod
    def insert(
        self, message: ChatMessage, tx_context: TransactionContext
    ) -> ChatMessage:
        pass

    @abstractmethod
    def delete(self, filter=None, tx_context: TransactionContext = None):
        pass

    @abstractmethod
    def delete_for_workspace(
        self, workspace_id: str, tx_context: TransactionContext = None
    ) -> None:
        pass
