from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Optional

from .models import ChatMessage, Conversation, Org, User
from .tx import TransactionContext


class OrgStore(ABC):
    @property
    def logger(self) -> Logger:
        raise NotImplementedError()

    @abstractmethod
    def get_by_id(self, org_id: str, tx_context: TransactionContext) -> Optional[Org]:
        pass

    @abstractmethod
    def insert(self, org: Org, tx_context: TransactionContext) -> Org:
        pass

    @abstractmethod
    def delete(self, org: Org, tx_context: TransactionContext):
        pass


class OrgStoreHooks(ABC):
    @abstractmethod
    def pre_insert(self, org: Org, tx_context: TransactionContext):
        pass

    @abstractmethod
    def pre_delete(self, org: Org, tx_context: TransactionContext):
        pass


# This is here just because the injector for some reason is not handling Optional injection
class OrgStoreHooksPass(OrgStoreHooks):
    def pre_insert(self, org: Org, tx_context: TransactionContext):
        pass

    def pre_delete(self, org: Org, tx_context: TransactionContext):
        pass


class OrgStoreProxy:
    def __init__(self, store: OrgStore, hooks: OrgStoreHooks):
        self._store = store
        self._hooks = hooks

    def get_by_id(self, org_id: str, tx_context: TransactionContext) -> Optional[Org]:
        return self._store.get_by_id(org_id, tx_context)

    def insert(self, org: Org, tx_context: TransactionContext) -> Org:
        if self._hooks:
            self._hooks.pre_insert(org, tx_context)
        return self._store.insert(org, tx_context)

    def delete(self, org: Org, tx_context: TransactionContext):
        if self._hooks:
            self._hooks.pre_delete(org, tx_context)
        return self._store.delete(org, tx_context)


class UserStore(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def list_orgs_for_user(self, user_id: str) -> list[Org]:
        pass


class ConversationStore(ABC):
    @property
    def logger(self) -> Logger:
        raise NotImplementedError()

    @abstractmethod
    def get_by_id(
        self,
        org_id: str,
        conversation_id: str,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ) -> Optional[Conversation]:
        pass

    @abstractmethod
    def get_by_external_id(
        self,
        org_id: str,
        external_id: str,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ) -> Optional[Conversation]:
        pass

    @abstractmethod
    def list(
        self,
        org_id: str,
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
    def delete_for_org(
        self, org_id: str, tx_context: TransactionContext = None
    ) -> None:
        pass


class ChatMessageStore(ABC):
    @property
    def logger(self) -> Logger:
        raise NotImplementedError()

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
    def delete_for_org(
        self, org_id: str, tx_context: TransactionContext = None
    ) -> None:
        pass
