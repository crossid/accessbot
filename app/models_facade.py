from abc import ABC, abstractmethod
from logging import Logger
from typing import Optional

from app.models import AccessRequest, ChatMessage, Org
from app.tx import TransactionContext


class OrgFacade(ABC):
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


class OrgFacadeHooks(ABC):
    @abstractmethod
    def pre_insert(self, org: Org, tx_context: TransactionContext):
        pass

    @abstractmethod
    def pre_delete(self, org: Org, tx_context: TransactionContext):
        pass


class OrgFacadeProxy:
    def __init__(self, facade: OrgFacade, hooks: OrgFacadeHooks):
        self._facade = facade
        self._hooks = hooks

    def get_by_id(self, org_id: str, tx_context: TransactionContext) -> Optional[Org]:
        return self._facade.get_by_id(org_id, tx_context)

    def insert(self, org: Org, tx_context: TransactionContext) -> Org:
        if self._hooks:
            self._hooks.pre_insert(org, tx_context)
        return self._facade.insert(org, tx_context)

    def delete(self, org: Org, tx_context: TransactionContext):
        if self._hooks:
            self._hooks.pre_delete(org, tx_context)
        return self._facade.delete(org, tx_context)


class RequestFacade(ABC):
    @property
    def logger(self) -> Logger:
        raise NotImplementedError()

    @abstractmethod
    def get_by_id(
        self,
        org_id: str,
        request_id: str,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ):
        pass

    @abstractmethod
    def insert(
        self, request: AccessRequest, tx_context: TransactionContext
    ) -> AccessRequest:
        pass

    @abstractmethod
    def delete_for_org(
        self, org_id: str, tx_context: TransactionContext = None
    ) -> None:
        pass


class ChatMessageFacade(ABC):
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
